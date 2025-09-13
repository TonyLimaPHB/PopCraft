import os
import shutil
import subprocess
import tempfile
import re
import hashlib
import csv
import json
import datetime
import sys

# ---------------- Configurações ----------------
SUPPORTED_FORMATS = ['.iso', '.bin', '.cue', '.mdf', '.ecm', '.img', '.chd', '.gdi', '.zso']  # ✅ ADICIONADO .ZSO
POPS_ELF_NAME = "POPS.ELF"
BIOS_FILE_NAME = "BIOS.BIN"
SLOT0_VMC_NAME = "SLOT0.VMC"
SLOT1_VMC_NAME = "SLOT1.VMC"
POPS_DIR_NAME = "POPS"
ART_DIR_NAME = "ART"

CHDMAN_EXE = "chdman.exe"
CUE2POPS_EXE = "cue2pops.exe"
POPS2CUE_EXE = "POPS2CUE.EXE"
VCD2ISO_EXE = "vcd2iso.exe"
ZISO_EXE = "ziso.exe"  # ✅ NOVA CONSTANTE PARA CONVERSÃO ZSO

# ---------------- Funções utilitárias ----------------
def get_script_root():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def copy_file(src, dest):
    ensure_dir(os.path.dirname(dest))
    if os.path.exists(src):
        shutil.copy2(src, dest)

def copy_tree(src, dst, log_callback=None):
    if not os.path.exists(src):
        if log_callback: log_callback(f"⚠️ Pasta de origem não encontrada: {src}")
        return False
    ensure_dir(dst)
    try:
        for item in os.listdir(src):
            s = os.path.join(src, item)
            d = os.path.join(dst, item)
            if os.path.isdir(s):
                shutil.copytree(s, d, dirs_exist_ok=True)
            else:
                shutil.copy2(s, d)
        if log_callback: log_callback(f"✅ Copiado: {src} → {dst}")
        return True
    except Exception as e:
        if log_callback: log_callback(f"❌ Erro ao copiar {src} → {dst}: {e}")
        return False

def get_file_hash(file_path):
    if not os.path.exists(file_path):
        return None
    hasher = hashlib.sha256()
    try:
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()[:8]
    except:
        return "ERROR"

# ---------------- Conversões Avançadas ----------------
def convert_chd_to_iso_temp(chd_path, log_callback=None, progress_callback=None):
    temp_base = "C:\\Temp"
    if not os.path.exists(temp_base):
        try:
            os.makedirs(temp_base, exist_ok=True)
        except PermissionError:
            temp_base = tempfile.gettempdir()
    temp_dir = tempfile.mkdtemp(prefix="POPSTEMP_", dir=temp_base)
    game_name = os.path.splitext(os.path.basename(chd_path))[0]
    cue_path = os.path.join(temp_dir, f"{game_name}.cue")
    bin_path = os.path.join(temp_dir, f"{game_name}.bin")
    comando = [CHDMAN_EXE, "extractcd", "-i", chd_path, "-o", cue_path, "-ob", bin_path]
    try:
        if log_callback:
            log_callback(f"▶️ Iniciando extração de {os.path.basename(chd_path)}...")
        if progress_callback:
            progress_callback("Iniciando...", 0)
        process = subprocess.Popen(
            comando,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            encoding='utf-8',
            errors='replace'
        )
        last_pct = 0
        if log_callback:
            log_callback("   Aguarde...")
        for line in process.stdout:
            line = line.strip()
            if not line:
                continue
            pct_match = re.search(r"(\d+)%", line)
            if pct_match:
                pct = int(pct_match.group(1))
                if pct != last_pct:
                    last_pct = pct
                    if progress_callback:
                        progress_callback(f"Extraindo {os.path.basename(chd_path)}", pct)
                    if log_callback:
                        log_callback(f"   {line}")
            elif "Extracting" in line or "Writing" in line or "Creating" in line:
                if log_callback:
                    log_callback(f"   {line}")
        process.wait()
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, comando)
        if log_callback:
            log_callback(f"✅ Extração concluída: {os.path.basename(chd_path)}")
            log_callback(f"   Arquivos gerados em: {temp_dir}")
        return cue_path, bin_path, temp_dir
    except FileNotFoundError:
        if log_callback: log_callback(f"❌ Erro: {CHDMAN_EXE} não encontrado!")
        return None, None, None
    except subprocess.CalledProcessError as e:
        if log_callback: log_callback(f"❌ Falha ao converter {chd_path}: código {e.returncode}")
        if 'temp_dir' in locals():
            shutil.rmtree(temp_dir, ignore_errors=True)
        return None, None, None
    except Exception as e:
        if log_callback: log_callback(f"❌ Erro inesperado: {e}")
        if 'temp_dir' in locals():
            shutil.rmtree(temp_dir, ignore_errors=True)
        return None, None, None

def convert_to_vcd(source_path, output_path, log_callback=None):
    if log_callback: log_callback(f"📦 Criando VCD: {os.path.basename(output_path)}...")
    shutil.copy2(source_path, output_path)
    if log_callback: log_callback(f"✅ VCD criado: {os.path.basename(output_path)}")
    return True

def convert_vcd_to_iso(vcd_path, output_iso, log_callback=None):
    script_root = get_script_root()
    vcd2iso_path = os.path.join(script_root, VCD2ISO_EXE)
    if not os.path.exists(vcd2iso_path):
        if log_callback: log_callback(f"❌ {VCD2ISO_EXE} não encontrado!")
        return False
    comando = [vcd2iso_path, vcd_path, output_iso]
    try:
        if log_callback: log_callback(f"▶️ Convertendo {os.path.basename(vcd_path)} → ISO...")
        result = subprocess.run(comando, capture_output=True, text=True, encoding='utf-8', errors='replace')
        if result.returncode != 0:
            if log_callback: log_callback(f"❌ Falha: {result.stderr}")
            return False
        if log_callback: log_callback(f"✅ ISO criado: {os.path.basename(output_iso)}")
        return True
    except Exception as e:
        if log_callback: log_callback(f"❌ Erro: {e}")
        return False

# ✅ ✅ ✅ FUNÇÃO CORRIGIDA: Usa POPS2CUE.EXE para VCD → CUE+BIN (IGNORA returncode)
def convert_vcd_to_cue_bin_with_pops2cue(vcd_path, log_callback=None):
    """
    Converte um arquivo .VCD em .CUE + .BIN usando o POPS2CUE.EXE.
    Ignora o returncode do processo e verifica apenas se os arquivos foram criados.
    Comando usado: POPS2CUE.EXE "arquivo.vcd"
    """
    script_root = get_script_root()
    pops2cue_path = os.path.join(script_root, POPS2CUE_EXE)
    if not os.path.exists(pops2cue_path):
        if log_callback: log_callback(f"❌ {POPS2CUE_EXE} não encontrado!")
        return False
    comando = [pops2cue_path, vcd_path]
    try:
        if log_callback: log_callback(f"▶️ Executando: {' '.join(comando)}")
        if log_callback: log_callback(f"▶️ Convertendo {os.path.basename(vcd_path)} → CUE+BIN...")
        process = subprocess.Popen(
            comando,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            encoding='utf-8',
            errors='replace',
            cwd=os.path.dirname(vcd_path)
        )
        output_lines = []
        for line in process.stdout:
            line = line.strip()
            output_lines.append(line)
            if log_callback:
                log_callback(f"   {line}")
        process.wait()
        # ✅ VERIFICA APENAS SE OS ARQUIVOS FORAM CRIADOS
        base_name = os.path.splitext(vcd_path)[0]
        output_cue = f"{base_name}.cue"
        output_bin = f"{base_name}.bin"
        if os.path.exists(output_cue) and os.path.exists(output_bin):
            if log_callback: log_callback(f"✅ Gerado: {os.path.basename(output_cue)} + {os.path.basename(output_bin)}")
            return True
        else:
            if log_callback: log_callback(f"❌ Arquivos CUE/BIN não foram gerados pelo POPS2CUE.EXE!")
            if log_callback: log_callback(f"❌ Saída do POPS2CUE: {' | '.join(output_lines)}")
            return False
    except Exception as e:
        if log_callback: log_callback(f"❌ Erro inesperado: {str(e)}")
        return False

def convert_cue_to_vcd(cue_path, vcd_output, log_callback=None):
    script_root = get_script_root()
    cue2pops_path = os.path.join(script_root, CUE2POPS_EXE)
    if not os.path.exists(cue2pops_path):
        if log_callback: log_callback(f"❌ {CUE2POPS_EXE} não encontrado!")
        return False
    bin_path = os.path.splitext(cue_path)[0] + ".bin"
    if not os.path.exists(bin_path):
        if log_callback: log_callback(f"❌ Arquivo BIN não encontrado: {bin_path}")
        return False
    comando = [cue2pops_path, cue_path, vcd_output]
    try:
        if log_callback: log_callback(f"▶️ Convertendo {os.path.basename(cue_path)} → VCD...")
        result = subprocess.run(comando, capture_output=True, text=True, encoding='utf-8', errors='replace')
        if result.returncode != 0:
            if log_callback: log_callback(f"❌ Falha: {result.stderr}")
            return False
        if log_callback: log_callback(f"✅ VCD criado: {os.path.basename(vcd_output)}")
        return True
    except Exception as e:
        if log_callback: log_callback(f"❌ Erro: {e}")
        return False

# ✅ NOVAS FUNÇÕES PARA CONVERSÃO COM CHDMAN
def convert_to_chd(input_path, output_chd, log_callback=None):
    script_root = get_script_root()
    chdman_path = os.path.join(script_root, CHDMAN_EXE)
    if not os.path.exists(chdman_path):
        if log_callback: log_callback(f"❌ {CHDMAN_EXE} não encontrado!")
        return False

    ext = os.path.splitext(input_path)[1].lower()

    # Se for ISO sem CUE, gera um CUE temporário
    cue_path = None
    if ext == ".iso":
        cue_path = os.path.splitext(input_path)[0] + ".cue"
        if not os.path.exists(cue_path):
            try:
                with open(cue_path, "w", encoding="utf-8") as f:
                    f.write(f'FILE "{os.path.basename(input_path)}" BINARY\n')
                    f.write("  TRACK 01 MODE2/2352\n")
                    f.write("    INDEX 01 00:00:00\n")
                if log_callback: log_callback(f"📝 CUE temporário criado: {cue_path}")
            except Exception as e:
                if log_callback: log_callback(f"❌ Erro ao criar CUE: {e}")
                return False
    elif ext == ".cue":
        cue_path = input_path
    else:
        if log_callback: log_callback(f"❌ Formato não suportado para conversão: {ext}")
        return False

    comando = [chdman_path, "createcd", "-i", cue_path, "-o", output_chd]
    try:
        if log_callback: log_callback(f"▶️ Convertendo {os.path.basename(cue_path)} → {os.path.basename(output_chd)}...")
        result = subprocess.run(comando, capture_output=True, text=True, encoding='utf-8', errors='replace')
        if result.returncode != 0:
            if log_callback: log_callback(f"❌ Falha: {result.stderr}")
            return False
        if log_callback: log_callback(f"✅ CHD criado: {os.path.basename(output_chd)}")
        return True
    except Exception as e:
        if log_callback: log_callback(f"❌ Erro: {e}")
        return False


def convert_chd_to_gdi(chd_path, output_gdi, log_callback=None):
    script_root = get_script_root()
    chdman_path = os.path.join(script_root, CHDMAN_EXE)
    if not os.path.exists(chdman_path):
        if log_callback: log_callback(f"❌ {CHDMAN_EXE} não encontrado!")
        return False
    comando = [chdman_path, "extractcd", "-i", chd_path, "-o", output_gdi]
    try:
        if log_callback: log_callback(f"▶️ Convertendo {os.path.basename(chd_path)} → GDI...")
        result = subprocess.run(comando, capture_output=True, text=True, encoding='utf-8', errors='replace')
        if result.returncode != 0:
            if log_callback: log_callback(f"❌ Falha: {result.stderr}")
            return False
        if log_callback: log_callback(f"✅ GDI criado: {os.path.basename(output_gdi)}")
        return True
    except Exception as e:
        if log_callback: log_callback(f"❌ Erro: {e}")
        return False

def convert_chd_to_iso_only(chd_path, output_iso, log_callback=None):
    script_root = get_script_root()
    chdman_path = os.path.join(script_root, CHDMAN_EXE)
    if not os.path.exists(chdman_path):
        if log_callback: log_callback(f"❌ {CHDMAN_EXE} não encontrado!")
        return False
    temp_cue = os.path.splitext(output_iso)[0] + ".cue"
    comando = [chdman_path, "extractcd", "-i", chd_path, "-o", temp_cue, "-ob", output_iso]
    try:
        if log_callback: log_callback(f"▶️ Convertendo {os.path.basename(chd_path)} → ISO...")
        result = subprocess.run(comando, capture_output=True, text=True, encoding='utf-8', errors='replace')
        if result.returncode != 0:
            if log_callback: log_callback(f"❌ Falha: {result.stderr}")
            return False
        if os.path.exists(temp_cue):
            os.remove(temp_cue)
        if log_callback: log_callback(f"✅ ISO criado: {os.path.basename(output_iso)}")
        return True
    except Exception as e:
        if log_callback: log_callback(f"❌ Erro: {e}")
        return False

# ✅ ✅ ✅ NOVAS FUNÇÕES: ISO ↔ ZSO COM AMBIENTE ISOLADO E LIMPEZA AUTOMÁTICA
def convert_iso_to_zso(iso_path, output_zso, log_callback=None):
    """Converte ISO → ZSO em ambiente isolado: copia ziso.exe e usa pasta temporária dentro da pasta do jogo."""
    script_root = get_script_root()
    ziso_exe = os.path.join(script_root, ZISO_EXE)

    if not os.path.exists(ziso_exe):
        if log_callback:
            log_callback(f"❌ {ZISO_EXE} não encontrado na pasta do script.")
        return False

    if not os.path.exists(iso_path):
        if log_callback:
            log_callback(f"❌ Arquivo ISO não encontrado: {iso_path}")
        return False

    # ✅ GARANTIR QUE A PASTA DE SAÍDA EXISTA (NOVA LINHA)
    ensure_dir(os.path.dirname(output_zso))

    # ✅ Obter pasta do arquivo ISO (não a raiz do script!)
    iso_dir = os.path.dirname(iso_path)
    iso_filename = os.path.basename(iso_path)
    iso_name_no_ext = os.path.splitext(iso_filename)[0]

    # ✅ Criar pastas temporárias dentro da pasta do jogo
    iso_temp_dir = os.path.join(iso_dir, "ISO")
    zso_temp_dir = os.path.join(iso_dir, "ZSO")
    ensure_dir(iso_temp_dir)
    ensure_dir(zso_temp_dir)

    # ✅ Caminhos temporários
    temp_iso_path = os.path.join(iso_temp_dir, iso_filename)
    temp_ziso_exe = os.path.join(iso_temp_dir, ZISO_EXE)
    temp_zso_path = os.path.join(zso_temp_dir, f"{iso_name_no_ext}.zso")

    try:
        # ✅ Passo 1: MOVER o arquivo ISO para a pasta ISO/ (NÃO COPIAR!)
        if log_callback:
            log_callback(f"📁 Movendo ISO para ambiente temporário: {iso_filename}")
        shutil.move(iso_path, temp_iso_path)  # ✅ MOVIMENTAÇÃO REAL — ORIGINAL AGORA ESTÁ AQUI

        # ✅ Passo 2: Copiar ziso.exe para a pasta ISO/
        if log_callback:
            log_callback(f"🔧 Copiando {ZISO_EXE} para ambiente temporário...")
        shutil.copy2(ziso_exe, temp_ziso_exe)

        # ✅ Passo 3: Executar conversão usando -c9 (sintaxe correta para a maioria dos ziso.exe)
        if log_callback:
            log_callback(f"▶️ Convertendo {iso_filename} → {iso_name_no_ext}.zso (ambiente isolado)...")
        
        # ✅ ✅ ✅ CORREÇÃO CRÍTICA: Usa -c9, NÃO -c -l 9
        comando = [temp_ziso_exe, "-c9", temp_iso_path, temp_zso_path]
        result = subprocess.run(
            comando,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            cwd=iso_temp_dir  # ✅ Executa dentro da pasta ISO/
        )

        if result.returncode != 0:
            if log_callback:
                log_callback(f"❌ Falha na conversão ISO → ZSO: {result.stderr.strip()}")
            return False

        # ✅ Passo 4: Verificar se o ZSO foi gerado
        if not os.path.exists(temp_zso_path):
            if log_callback:
                log_callback(f"❌ Arquivo ZSO não foi gerado após conversão!")
            return False

        # ✅ Passo 5: Mover o ZSO resultante para a pasta de saída escolhida
        if log_callback:
            log_callback(f"📤 Movendo ZSO resultante para destino final: {os.path.basename(output_zso)}")
        shutil.move(temp_zso_path, output_zso)

        # ✅ PASSO 6: RESTAURAR O ARQUIVO ORIGINAL (ISO) PARA ONDE ESTAVA — ANTES DA LIMPEZA!
        if log_callback:
            log_callback(f"🔄 Restaurando ISO original para local: {iso_path}")
        shutil.move(temp_iso_path, iso_path)  # ✅ AGORA O ORIGINAL VOLTA!

        # ✅ Passo 7: Limpeza: apagar pastas temporárias e ziso.exe
        if log_callback:
            log_callback(f"🧹 Limpando ambiente temporário...")

        # Remove o ziso.exe copiado
        if os.path.exists(temp_ziso_exe):
            os.remove(temp_ziso_exe)

        # Remove a pasta ISO (vazia agora)
        if os.path.exists(iso_temp_dir) and len(os.listdir(iso_temp_dir)) == 0:
            os.rmdir(iso_temp_dir)

        # Remove a pasta ZSO (vazia agora)
        if os.path.exists(zso_temp_dir) and len(os.listdir(zso_temp_dir)) == 0:
            os.rmdir(zso_temp_dir)

        if log_callback:
            log_callback(f"✅ Conversão ISO → ZSO concluída com sucesso!")
            log_callback(f"   Arquivo final: {output_zso}")

        return True

    except Exception as e:
        if log_callback:
            log_callback(f"❌ Erro durante conversão ISO → ZSO: {e}")

        # ✅ RESTAURA O ARQUIVO ORIGINAL EM CASO DE ERRO
        try:
            if os.path.exists(temp_iso_path) and not os.path.exists(iso_path):
                shutil.move(temp_iso_path, iso_path)  # ✅ DEVOLVE O ISO ORIGINAL PARA ONDE ESTAVA
                if log_callback:
                    log_callback(f"🔄 Arquivo ISO original restaurado: {iso_path}")
        except Exception as restore_error:
            if log_callback:
                log_callback(f"⚠️ Falha ao restaurar ISO original: {restore_error}")

        # ✅ LIMPEZA FINAL — APENAS AS PASTAS TEMPORÁRIAS
        try:
            if 'temp_ziso_exe' in locals() and os.path.exists(temp_ziso_exe):
                os.remove(temp_ziso_exe)
            if os.path.exists(iso_temp_dir):
                shutil.rmtree(iso_temp_dir, ignore_errors=True)
            if os.path.exists(zso_temp_dir):
                shutil.rmtree(zso_temp_dir, ignore_errors=True)
        except:
            pass
        return False


def convert_zso_to_iso(zso_path, output_iso, log_callback=None):
    """Converte ZSO → ISO em ambiente isolado usando ziso.exe"""
    script_root = get_script_root()
    ziso_exe = os.path.join(script_root, ZISO_EXE)

    if not os.path.exists(ziso_exe):
        if log_callback:
            log_callback(f"❌ {ZISO_EXE} não encontrado na pasta do script.")
        return False

    if not os.path.exists(zso_path):
        if log_callback:
            log_callback(f"❌ Arquivo ZSO não encontrado: {zso_path}")
        return False

    # ✅ GARANTIR QUE A PASTA DE SAÍDA EXISTA (NOVA LINHA)
    ensure_dir(os.path.dirname(output_iso))

    # Obter pasta do arquivo ZSO
    zso_dir = os.path.dirname(zso_path)
    zso_filename = os.path.basename(zso_path)
    zso_name_no_ext = os.path.splitext(zso_filename)[0]

    # Criar pastas temporárias dentro da pasta do jogo
    zso_temp_dir = os.path.join(zso_dir, "ZSO")
    iso_temp_dir = os.path.join(zso_dir, "ISO")
    ensure_dir(zso_temp_dir)
    ensure_dir(iso_temp_dir)

    # Caminhos temporários
    temp_zso_path = os.path.join(zso_temp_dir, zso_filename)
    temp_ziso_exe = os.path.join(zso_temp_dir, ZISO_EXE)
    temp_iso_path = os.path.join(iso_temp_dir, f"{zso_name_no_ext}.iso")

    try:
        # ✅ Passo 1: MOVER o arquivo ZSO para a pasta ZSO/ (NÃO COPIAR!)
        if log_callback:
            log_callback(f"📁 Movendo ZSO para ambiente temporário: {zso_filename}")
        shutil.move(zso_path, temp_zso_path)  # ✅ MOVIMENTAÇÃO REAL — ORIGINAL AGORA ESTÁ AQUI

        # ✅ Passo 2: Copiar ziso.exe para a pasta ZSO/
        if log_callback:
            log_callback(f"🔧 Copiando {ZISO_EXE} para ambiente temporário...")
        shutil.copy2(ziso_exe, temp_ziso_exe)

        # ✅ Passo 3: Executar conversão usando -c 0 (extração)
        if log_callback:
            log_callback(f"▶️ Convertendo {zso_filename} → {zso_name_no_ext}.iso (ambiente isolado)...")
        
        # Usa -c 0 para descompactar, não -x
        comando = [temp_ziso_exe, "-c", "0", temp_zso_path, temp_iso_path]
        result = subprocess.run(
            comando,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            cwd=zso_temp_dir  # Executa dentro da pasta ZSO/
        )

        # Captura de erro detalhada
        if result.returncode != 0:
            if log_callback:
                log_callback(f"❌ Falha na conversão ZSO → ISO: {result.stderr.strip()}")
                log_callback(f"📝 Detalhes do erro: {result.stdout.strip()}")
            return False

        # Passo 4: Verificar se o ISO foi gerado
        if not os.path.exists(temp_iso_path):
            if log_callback:
                log_callback(f"❌ Arquivo ISO não foi gerado após conversão!")
            return False

        # ✅ Passo 5: Mover o ISO resultante para a pasta de saída escolhida
        if log_callback:
            log_callback(f"📤 Movendo ISO resultante para destino final: {os.path.basename(output_iso)}")
        shutil.move(temp_iso_path, output_iso)

        # ✅ PASSO 6: RESTAURAR O ARQUIVO ORIGINAL (ZSO) PARA ONDE ESTAVA — ANTES DA LIMPEZA!
        if log_callback:
            log_callback(f"🔄 Restaurando ZSO original para local: {zso_path}")
        shutil.move(temp_zso_path, zso_path)  # ✅ AGORA O ORIGINAL VOLTA!

        # ✅ Passo 7: Limpeza: apagar pastas temporárias e ziso.exe
        if log_callback:
            log_callback(f"🧹 Limpando ambiente temporário...")

        # Remove o ziso.exe copiado
        if os.path.exists(temp_ziso_exe):
            os.remove(temp_ziso_exe)

        # Remove a pasta ZSO (vazia agora)
        if os.path.exists(zso_temp_dir) and len(os.listdir(zso_temp_dir)) == 0:
            os.rmdir(zso_temp_dir)

        # Remove a pasta ISO (vazia agora)
        if os.path.exists(iso_temp_dir) and len(os.listdir(iso_temp_dir)) == 0:
            os.rmdir(iso_temp_dir)

        if log_callback:
            log_callback(f"✅ Conversão ZSO → ISO concluída com sucesso!")
            log_callback(f"   Arquivo final: {output_iso}")

        return True

    except Exception as e:
        if log_callback:
            log_callback(f"❌ Erro durante conversão ZSO → ISO: {e}")

        # ✅ RESTAURA O ARQUIVO ORIGINAL EM CASO DE ERRO
        try:
            if os.path.exists(temp_zso_path) and not os.path.exists(zso_path):
                shutil.move(temp_zso_path, zso_path)  # ✅ DEVOLVE O ZSO ORIGINAL PARA ONDE ESTAVA
                if log_callback:
                    log_callback(f"🔄 Arquivo ZSO original restaurado: {zso_path}")
        except Exception as restore_error:
            if log_callback:
                log_callback(f"⚠️ Falha ao restaurar ZSO original: {restore_error}")

        # ✅ LIMPEZA FINAL — APENAS AS PASTAS TEMPORÁRIAS
        try:
            if 'temp_ziso_exe' in locals() and os.path.exists(temp_ziso_exe):
                os.remove(temp_ziso_exe)
            if os.path.exists(zso_temp_dir):
                shutil.rmtree(zso_temp_dir, ignore_errors=True)
            if os.path.exists(iso_temp_dir):
                shutil.rmtree(iso_temp_dir, ignore_errors=True)
        except:
            pass
        return False

# ---------------- Funções de Backup e Configuração ----------------
def backup_conf_file(target_dir):
    conf_file = os.path.join(target_dir, "conf_apps.cfg")
    if not os.path.exists(conf_file):
        return
    backup_dir = os.path.join(target_dir, "backup")
    ensure_dir(backup_dir)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"conf_apps_{timestamp}.bak"
    shutil.copy2(conf_file, os.path.join(backup_dir, backup_name))

def update_conf_apps(game_key, target_dir, elf_name):
    backup_conf_file(target_dir)
    conf_file = os.path.join(target_dir, "conf_apps.cfg")
    entry = f"{game_key}=mass:/{elf_name}\n"
    lines = []
    if os.path.exists(conf_file):
        with open(conf_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    updated = False
    new_lines = []
    for line in lines:
        if line.startswith(game_key + "="):
            new_lines.append(entry)
            updated = True
        else:
            new_lines.append(line)
    if not updated:
        new_lines.append(entry)
    with open(conf_file, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

def save_cover(elf_name_no_ext, art_dir, cover_path):
    ensure_dir(art_dir)
    ext = os.path.splitext(cover_path)[1]
    dest_path = os.path.join(art_dir, f"XX.{elf_name_no_ext}.ELF_COV{ext}")
    shutil.copy2(cover_path, dest_path)
    return dest_path

def save_logo(elf_name_no_ext, art_dir, logo_path):
    ensure_dir(art_dir)
    ext = os.path.splitext(logo_path)[1]
    dest_path = os.path.join(art_dir, f"XX.{elf_name_no_ext}.ELF_LGO{ext}")
    shutil.copy2(logo_path, dest_path)
    return dest_path

def get_elf_name_from_game_key(game_key, target_dir):
    conf_file = os.path.join(target_dir, "conf_apps.cfg")
    if not os.path.exists(conf_file):
        return None
    with open(conf_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith(game_key + "="):
                elf_path = line.split("=", 1)[1].strip()
                elf_name = os.path.basename(elf_path.replace("mass:/", ""))
                if elf_name.startswith("XX."):
                    return elf_name[3:-4]
                else:
                    return os.path.splitext(elf_name)[0]
    return None

def process_game(file_path, pops_dir, target_dir, cover_path=None, logo_path=None, log_callback=None, progress_callback=None):
    original_name = os.path.basename(file_path)
    game_name, ext = os.path.splitext(original_name)
    ext = ext.lower()
    match = re.search(r"\[(.*?)\]", game_name)
    code_in_brackets = match.group(1) if match else None
    base_name = code_in_brackets if code_in_brackets else game_name
    elf_name = f"XX.{base_name}.ELF"
    elf_name_no_ext = base_name
    vcd_name = f"{code_in_brackets}.VCD" if code_in_brackets else f"{game_name}.VCD"
    save_folder_name = elf_name_no_ext
    conf_name = re.sub(r"\[.*?\]", "", game_name).strip()
    temp_dir = None

    if ext == ".chd":
        cue_path, bin_path, temp_dir = convert_chd_to_iso_temp(file_path, log_callback, progress_callback)
        if not cue_path or not bin_path:
            return False
        script_root = get_script_root()
        cue2pops_path = os.path.join(script_root, CUE2POPS_EXE)
        if not os.path.exists(cue2pops_path):
            if log_callback: log_callback(f"❌ {CUE2POPS_EXE} não encontrado!")
            if temp_dir: shutil.rmtree(temp_dir, ignore_errors=True)
            return False
        vcd_output = os.path.join(pops_dir, vcd_name)
        comando_cue2pops = [cue2pops_path, cue_path, vcd_output]
        try:
            if log_callback: log_callback(f"▶️ Convertendo {os.path.basename(cue_path)} para VCD...")
            subprocess.run(comando_cue2pops, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            if log_callback: log_callback(f"✅ VCD criado: {os.path.basename(vcd_output)}")
        except Exception as e:
            if log_callback: log_callback(f"❌ Falha ao converter CUE para VCD: {e}")
            if temp_dir: shutil.rmtree(temp_dir, ignore_errors=True)
            return False
        file_path = None
    else:
        vcd_path = os.path.join(pops_dir, vcd_name)
        convert_to_vcd(file_path, vcd_path, log_callback)

    save_folder = os.path.join(pops_dir, save_folder_name)
    ensure_dir(save_folder)
    copy_file(SLOT0_VMC_NAME, os.path.join(save_folder, SLOT0_VMC_NAME))
    copy_file(SLOT1_VMC_NAME, os.path.join(save_folder, SLOT1_VMC_NAME))

    script_root = get_script_root()
    fix_src = os.path.join(script_root, "_pops_fix", elf_name_no_ext)
    if os.path.exists(fix_src):
        if log_callback: log_callback(f"🔧 Aplicando fix para {elf_name_no_ext}...")
        copy_tree(fix_src, save_folder, log_callback)

    outside_elf = os.path.join(target_dir, elf_name)
    copy_file(POPS_ELF_NAME, outside_elf)
    update_conf_apps(conf_name, target_dir, elf_name)

    art_dir = os.path.join(target_dir, ART_DIR_NAME)
    if cover_path:
        save_cover(elf_name_no_ext, art_dir, cover_path)
    if logo_path:
        save_logo(elf_name_no_ext, art_dir, logo_path)

    if temp_dir:
        shutil.rmtree(temp_dir, ignore_errors=True)

    return True