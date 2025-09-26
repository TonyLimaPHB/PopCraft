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
SUPPORTED_FORMATS = ['.iso', '.bin', '.cue', '.mdf', '.ecm', '.img', '.chd', '.gdi', '.zso']
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
ZISO_EXE = "ziso.exe"

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
    """Copia recursivamente uma pasta, mantendo estrutura e sobrescrevendo apenas se necessário."""
    if not os.path.exists(src):
        if log_callback: log_callback(f"⚠️ Pasta de origem não encontrada: {src}")
        return False
    ensure_dir(dst)
    try:
        for item in os.listdir(src):
            s = os.path.join(src, item)
            d = os.path.join(dst, item)
            if os.path.isdir(s):
                if os.path.exists(d):
                    # Se pasta existe, entra recursivamente (merge)
                    copy_tree(s, d, log_callback)
                else:
                    shutil.copytree(s, d, dirs_exist_ok=False)
            else:
                # Se arquivo existe, compara conteúdo antes de sobrescrever
                if os.path.exists(d):
                    if os.path.getsize(s) == os.path.getsize(d):
                        with open(s, 'rb') as f1, open(d, 'rb') as f2:
                            if f1.read() == f2.read():
                                if log_callback: log_callback(f"✅ Ignorado (igual): {item}", "info")
                                continue
                shutil.copy2(s, d)
        if log_callback: log_callback(f"✅ Copiado: {src} → {dst}")
        return True
    except Exception as e:
        if log_callback: log_callback(f"❌ Erro ao copiar {src} → {dst}: {e}")
        return False

def get_file_hash(file_path):
    """Retorna hash SHA256 dos primeiros 8 caracteres do arquivo."""
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
    """Extrai CHD para CUE+BIN usando chdman.exe. Usa temp dir seguro."""
    temp_base = os.environ.get('TEMP', tempfile.gettempdir())
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
            if log_callback: log_callback(f"   Esperado: {output_cue} + {output_bin}")
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

# ✅ ✅ ✅ CORREÇÃO CRÍTICA: CHD → ISO DIRETO (SEM CUE TEMPORÁRIA)
def convert_chd_to_iso_only(chd_path, output_iso, log_callback=None):
    script_root = get_script_root()
    chdman_path = os.path.join(script_root, CHDMAN_EXE)
    if not os.path.exists(chdman_path):
        if log_callback: log_callback(f"❌ {CHDMAN_EXE} não encontrado!")
        return False
    base_name = os.path.splitext(output_iso)[0]
    chd_dir = os.path.dirname(chd_path)
    temp_cue = os.path.join(chd_dir, f"{base_name}.cue")
    temp_bin = os.path.join(chd_dir, f"{base_name}.bin")
    comando = [chdman_path, "extractcd", "-i", chd_path, "-o", temp_cue, "-ob", temp_bin]
    try:
        if log_callback: 
            log_callback(f"▶️  Convertendo {os.path.basename(chd_path)} → ISO...")
        result = subprocess.run(
            comando,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        if result.returncode != 0:
            if log_callback:
                log_callback(f"❌ Falha na extração: {result.stderr.strip()}")
            return False
        if not os.path.exists(temp_bin) or os.path.getsize(temp_bin) == 0:
            if log_callback:
                log_callback(f"❌ Arquivo BIN não gerado ou vazio: {temp_bin}")
            return False
        size_mb = os.path.getsize(temp_bin) / (1024 * 1024)
        if log_callback:
            log_callback(f"   ✅ Extraído: {os.path.basename(temp_bin)} ({size_mb:.1f} MB)")
        if log_callback: 
            log_callback(f"   🔄 Renomeando {os.path.basename(temp_bin)} → {os.path.basename(output_iso)}...")
        shutil.move(temp_bin, output_iso)
        if os.path.exists(temp_cue):
            os.remove(temp_cue)
            if log_callback: 
                log_callback(f"   🗑️  Limpeza concluída: {os.path.basename(temp_cue)} removido")
        if log_callback: 
            log_callback(f"🎉 ISO criado com sucesso: {os.path.basename(output_iso)}")
        return True
    except Exception as e:
        if log_callback: 
            log_callback(f"❌ Erro inesperado: {e}")
        try:
            if os.path.exists(temp_cue): os.remove(temp_cue)
            if os.path.exists(temp_bin): os.remove(temp_bin)
        except:
            pass
        return False

# ✅ ✅ ✅ NOVAS FUNÇÕES: ISO ↔ ZSO COM AMBIENTE ISOLADO E LIMPEZA AUTOMÁTICA
def convert_iso_to_zso(iso_path, output_zso, log_callback=None):
    script_root = get_script_root()
    ziso_exe = os.path.join(script_root, ZISO_EXE)
    if not os.path.exists(ziso_exe):
        if log_callback: log_callback(f"❌ {ZISO_EXE} não encontrado na pasta do script.")
        return False
    if not os.path.exists(iso_path):
        if log_callback: log_callback(f"❌ Arquivo ISO não encontrado: {iso_path}")
        return False
    ensure_dir(os.path.dirname(output_zso))
    iso_dir = os.path.dirname(iso_path)
    iso_filename = os.path.basename(iso_path)
    iso_name_no_ext = os.path.splitext(iso_filename)[0]
    iso_temp_dir = os.path.join(iso_dir, "ISO")
    zso_temp_dir = os.path.join(iso_dir, "ZSO")
    ensure_dir(iso_temp_dir)
    ensure_dir(zso_temp_dir)
    temp_iso_path = os.path.join(iso_temp_dir, iso_filename)
    temp_ziso_exe = os.path.join(iso_temp_dir, ZISO_EXE)
    temp_zso_path = os.path.join(zso_temp_dir, f"{iso_name_no_ext}.zso")
    try:
        if log_callback: log_callback(f"📁 Movendo ISO para ambiente temporário: {iso_filename}")
        shutil.move(iso_path, temp_iso_path)
        if log_callback: log_callback(f"🔧 Copiando {ZISO_EXE} para ambiente temporário...")
        shutil.copy2(ziso_exe, temp_ziso_exe)
        if log_callback: log_callback(f"▶️ Convertendo {iso_filename} → {iso_name_no_ext}.zso (ambiente isolado)...")
        comando = [temp_ziso_exe, "-c9", temp_iso_path, temp_zso_path]
        result = subprocess.run(
            comando,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            cwd=iso_temp_dir
        )
        if result.returncode != 0:
            if log_callback: log_callback(f"❌ Falha na conversão ISO → ZSO: {result.stderr.strip()}")
            return False
        if not os.path.exists(temp_zso_path):
            if log_callback: log_callback(f"❌ Arquivo ZSO não foi gerado após conversão!")
            return False
        if log_callback: log_callback(f"📤 Movendo ZSO resultante para destino final: {os.path.basename(output_zso)}")
        shutil.move(temp_zso_path, output_zso)
        if log_callback: log_callback(f"🔄 Restaurando ISO original para local: {iso_path}")
        shutil.move(temp_iso_path, iso_path)
        if log_callback: log_callback(f"🧹 Limpando ambiente temporário...")
        if os.path.exists(temp_ziso_exe): os.remove(temp_ziso_exe)
        if os.path.exists(iso_temp_dir) and len(os.listdir(iso_temp_dir)) == 0: os.rmdir(iso_temp_dir)
        if os.path.exists(zso_temp_dir) and len(os.listdir(zso_temp_dir)) == 0: os.rmdir(zso_temp_dir)
        if log_callback: log_callback(f"✅ Conversão ISO → ZSO concluída com sucesso!")
        return True
    except Exception as e:
        if log_callback: log_callback(f"❌ Erro durante conversão ISO → ZSO: {e}")
        try:
            if os.path.exists(temp_iso_path) and not os.path.exists(iso_path):
                shutil.move(temp_iso_path, iso_path)
        except:
            pass
        try:
            if 'temp_ziso_exe' in locals() and os.path.exists(temp_ziso_exe): os.remove(temp_ziso_exe)
            if os.path.exists(iso_temp_dir): shutil.rmtree(iso_temp_dir, ignore_errors=True)
            if os.path.exists(zso_temp_dir): shutil.rmtree(zso_temp_dir, ignore_errors=True)
        except:
            pass
        return False

def convert_zso_to_iso(zso_path, output_iso, log_callback=None):
    script_root = get_script_root()
    ziso_exe = os.path.join(script_root, ZISO_EXE)
    if not os.path.exists(ziso_exe):
        if log_callback: log_callback(f"❌ {ZISO_EXE} não encontrado na pasta do script.")
        return False
    if not os.path.exists(zso_path):
        if log_callback: log_callback(f"❌ Arquivo ZSO não encontrado: {zso_path}")
        return False
    ensure_dir(os.path.dirname(output_iso))
    zso_dir = os.path.dirname(zso_path)
    zso_filename = os.path.basename(zso_path)
    zso_name_no_ext = os.path.splitext(zso_filename)[0]
    zso_temp_dir = os.path.join(zso_dir, "ZSO")
    iso_temp_dir = os.path.join(zso_dir, "ISO")
    ensure_dir(zso_temp_dir)
    ensure_dir(iso_temp_dir)
    temp_zso_path = os.path.join(zso_temp_dir, zso_filename)
    temp_ziso_exe = os.path.join(zso_temp_dir, ZISO_EXE)
    temp_iso_path = os.path.join(iso_temp_dir, f"{zso_name_no_ext}.iso")
    try:
        if log_callback: log_callback(f"📁 Movendo ZSO para ambiente temporário: {zso_filename}")
        shutil.move(zso_path, temp_zso_path)
        if log_callback: log_callback(f"🔧 Copiando {ZISO_EXE} para ambiente temporário...")
        shutil.copy2(ziso_exe, temp_ziso_exe)
        if log_callback: log_callback(f"▶️ Convertendo {zso_filename} → {zso_name_no_ext}.iso (ambiente isolado)...")
        comando = [temp_ziso_exe, "-c", "0", temp_zso_path, temp_iso_path]
        result = subprocess.run(
            comando,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            cwd=zso_temp_dir
        )
        if result.returncode != 0:
            if log_callback: log_callback(f"❌ Falha na conversão ZSO → ISO: {result.stderr.strip()}")
            return False
        if not os.path.exists(temp_iso_path):
            if log_callback: log_callback(f"❌ Arquivo ISO não foi gerado após conversão!")
            return False
        if log_callback: log_callback(f"📤 Movendo ISO resultante para destino final: {os.path.basename(output_iso)}")
        shutil.move(temp_iso_path, output_iso)
        if log_callback: log_callback(f"🔄 Restaurando ZSO original para local: {zso_path}")
        shutil.move(temp_zso_path, zso_path)
        if log_callback: log_callback(f"🧹 Limpando ambiente temporário...")
        if os.path.exists(temp_ziso_exe): os.remove(temp_ziso_exe)
        if os.path.exists(zso_temp_dir) and len(os.listdir(zso_temp_dir)) == 0: os.rmdir(zso_temp_dir)
        if os.path.exists(iso_temp_dir) and len(os.listdir(iso_temp_dir)) == 0: os.rmdir(iso_temp_dir)
        if log_callback: log_callback(f"✅ Conversão ZSO → ISO concluída com sucesso!")
        return True
    except Exception as e:
        if log_callback: log_callback(f"❌ Erro durante conversão ZSO → ISO: {e}")
        try:
            if os.path.exists(temp_zso_path) and not os.path.exists(zso_path):
                shutil.move(temp_zso_path, zso_path)
        except:
            pass
        try:
            if 'temp_ziso_exe' in locals() and os.path.exists(temp_ziso_exe): os.remove(temp_ziso_exe)
            if os.path.exists(zso_temp_dir): shutil.rmtree(zso_temp_dir, ignore_errors=True)
            if os.path.exists(iso_temp_dir): shutil.rmtree(iso_temp_dir, ignore_errors=True)
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

# [NOVO] - Função auxiliar para buscar e copiar descrição .cfg
def copy_description_cfg(game_code, script_root, target_dir, log_callback=None):
    """
    Procura por um arquivo .cfg com nome igual ao game_code dentro da pasta _description_psx.
    Aceita tanto '[SLUS_008.24]' quanto 'SLUS_008.24'.
    Cria a pasta 'CFG' na RAIZ do target_dir (ex: K:/CFG/) se não existir.
    COPIA o arquivo .cfg para lá (NÃO MOVE — mantém o original em _description_psx).
    Retorna True se encontrou e copiou, False caso contrário.
    """
    desc_dir = os.path.join(script_root, "_description_psx")
    
    # Verifica se a pasta _description_psx existe
    if not os.path.exists(desc_dir):
        if log_callback:
            log_callback(f"❌ Pasta '_description_psx' NÃO ENCONTRADA em: {desc_dir}")
        return False

    # Normaliza o código do jogo: remove colchetes se houver
    clean_code = game_code.strip()
    if clean_code.startswith('[') and clean_code.endswith(']'):
        clean_code = clean_code[1:-1].strip()

    # Nome esperado do arquivo .cfg
    cfg_filename = f"{clean_code}.cfg"
    cfg_path = os.path.join(desc_dir, cfg_filename)

    # Verifica se o arquivo .cfg existe
    if not os.path.isfile(cfg_path):
        if log_callback:
            log_callback(f"ℹ️ Arquivo '{cfg_filename}' não encontrado em '_description_psx'.")
        return False

    # ✅ PASSO CRÍTICO: Define a pasta CFG na RAIZ do diretório de saída
    cfg_target_dir = os.path.join(target_dir, "CFG")  # ← ISSO É K:/CFG!
    ensure_dir(cfg_target_dir)  # ✅ CRIA SE NÃO EXISTIR

    if log_callback:
        log_callback(f"✅ Pasta 'CFG' criada/verificada em: {cfg_target_dir}")

    dest_path = os.path.join(cfg_target_dir, cfg_filename)

    # Verifica se já existe no destino (comparação de conteúdo)
    if os.path.exists(dest_path):
        if os.path.getsize(cfg_path) == os.path.getsize(dest_path):
            with open(cfg_path, 'rb') as f1, open(dest_path, 'rb') as f2:
                if f1.read() == f2.read():
                    if log_callback:
                        log_callback(f"✅ Descrição já existe e é idêntica: {cfg_filename}")
                    return True
        try:
            os.remove(dest_path)
            if log_callback:
                log_callback(f"⚠️ Sobrescrevendo arquivo existente: {cfg_filename}")
        except Exception as e:
            if log_callback:
                log_callback(f"❌ Falha ao sobrescrever {cfg_filename}: {e}")
            return False

    # ✅ COPIA o arquivo (NÃO MOVE!) — O ORIGINAL PERMANECE EM _description_psx/
    try:
        shutil.copy2(cfg_path, dest_path)
        if log_callback:
            log_callback(f"📄 DESCRICAO COPIADA COM SUCESSO: {cfg_filename} → {dest_path}")
        return True

    except PermissionError:
        if log_callback:
            log_callback(f"❌ Permissão negada ao copiar {cfg_filename}. Verifique permissões da pasta.")
        return False
    except FileNotFoundError:
        if log_callback:
            log_callback(f"❌ Arquivo fonte não encontrado após validação: {cfg_path}")
        return False
    except Exception as e:
        if log_callback:
            log_callback(f"❌ Erro inesperado ao copiar {cfg_filename}: {e}")
        return False


# ✅ ✅ ✅ FUNÇÃO PRINCIPAL REVISADA: process_game com suporte perfeito a .cue/.bin + DESCRIÇÕES
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
    elif ext == ".cue":
        bin_path = os.path.splitext(file_path)[0] + ".bin"
        if not os.path.exists(bin_path):
            if log_callback: log_callback(f"❌ Arquivo BIN associado não encontrado: {bin_path}")
            return False
        script_root = get_script_root()
        cue2pops_path = os.path.join(script_root, CUE2POPS_EXE)
        if not os.path.exists(cue2pops_path):
            if log_callback: log_callback(f"❌ {CUE2POPS_EXE} não encontrado!")
            return False
        vcd_output = os.path.join(pops_dir, vcd_name)
        if log_callback: log_callback(f"▶️ Convertendo {os.path.basename(file_path)} + {os.path.basename(bin_path)} para VCD...")
        if not convert_cue_to_vcd(file_path, vcd_output, log_callback):
            return False
    elif ext == ".bin":
        cue_path = os.path.splitext(file_path)[0] + ".cue"
        if not os.path.exists(cue_path):
            if log_callback: log_callback(f"❌ Arquivo CUE associado não encontrado: {cue_path}")
            return False
        script_root = get_script_root()
        cue2pops_path = os.path.join(script_root, CUE2POPS_EXE)
        if not os.path.exists(cue2pops_path):
            if log_callback: log_callback(f"❌ {CUE2POPS_EXE} não encontrado!")
            return False
        vcd_output = os.path.join(pops_dir, vcd_name)
        if log_callback: log_callback(f"▶️ Convertendo {os.path.basename(cue_path)} + {os.path.basename(file_path)} para VCD...")
        if not convert_cue_to_vcd(cue_path, vcd_output, log_callback):
            return False
    else:
        vcd_path = os.path.join(pops_dir, vcd_name)
        if log_callback: log_callback(f"📦 Copiando arquivo original ({ext}) como VCD...")
        convert_to_vcd(file_path, vcd_path, log_callback)

    save_folder = os.path.join(pops_dir, save_folder_name)
    ensure_dir(save_folder)
    copy_file(SLOT0_VMC_NAME, os.path.join(save_folder, SLOT0_VMC_NAME))
    copy_file(SLOT1_VMC_NAME, os.path.join(save_folder, SLOT1_VMC_NAME))

    script_root = get_script_root()

    # [MUDANÇA] - Aplicar fix de _pops_fix (já existente)
    fix_src = os.path.join(script_root, "_pops_fix", elf_name_no_ext)
    if os.path.exists(fix_src):
        if log_callback: log_callback(f"🔧 Aplicando fix para {elf_name_no_ext}...")
        copy_tree(fix_src, save_folder, log_callback)

    # [NOVO] - Aplicar descrição .cfg de _description_psx
    # Usa o mesmo base_name (código do jogo) para procurar SLUS_XXX.XX.cfg
        # [CORREÇÃO FINAL] - Copia .cfg para a RAIZ da pasta de saída (mesmo nível da pasta POPS)
    if code_in_brackets:
        copy_description_cfg(code_in_brackets, script_root, target_dir, log_callback)
    else:
        copy_description_cfg(base_name, script_root, target_dir, log_callback)

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

# ✅ ✅ ✅ FUNÇÃO FINAL: Instalação USB com merge inteligente e ocultação
def install_usb_files(destination_dir, log_callback=None):
    """
    Copia TODA a estrutura da pasta 'usb_install/' (incluindo subpastas e arquivos)
    para o destino selecionado, e oculta todos os itens no Windows.
    
    Comportamento:
    - Se destino NÃO existe → cria e copia tudo
    - Se destino EXISTE → mescla (merge) o conteúdo sem apagar o que já está lá
    - Arquivos iguais são ignorados (comparação por conteúdo)
    - Pastas são copiadas recursivamente
    - Todos os itens são ocultados no Windows
    """
    script_root = get_script_root()
    usb_install_path = os.path.join(script_root, "usb_install")

    if not os.path.exists(usb_install_path):
        if log_callback: log_callback("❌ Pasta 'usb_install' não encontrada na raiz do script!", "error")
        return False

    items = os.listdir(usb_install_path)
    if not items:
        if log_callback: log_callback("⚠️ Pasta 'usb_install' está vazia. Nada para copiar.", "warning")
        return False

    total_items = len(items)
    if log_callback: log_callback(f"🚀 Iniciando instalação USB... ({total_items} itens)", "info")

    success_count = 0
    failed_count = 0
    skipped_count = 0

    for item in items:
        src = os.path.join(usb_install_path, item)
        dst = os.path.join(destination_dir, item)

        try:
            if os.path.isdir(src):
                # ✅ PASTA: Mescla recursivamente
                if os.path.exists(dst):
                    if log_callback: log_callback(f"📁 Mesclando pasta: {item}", "info")
                    copy_tree(src, dst, lambda msg: log_callback(msg, "info"))
                else:
                    shutil.copytree(src, dst)
                    if log_callback: log_callback(f"📁 Copiado diretório: {item}", "success")
            else:
                # ✅ ARQUIVO: Verifica se já existe e é igual
                if os.path.exists(dst):
                    if os.path.getsize(src) == os.path.getsize(dst):
                        with open(src, 'rb') as f1, open(dst, 'rb') as f2:
                            if f1.read() == f2.read():
                                if log_callback: log_callback(f"✅ Ignorado (igual): {item}", "info")
                                skipped_count += 1
                                continue
                    # Se diferente, sobrescreve
                    shutil.copy2(src, dst)
                    if log_callback: log_callback(f"📄 Atualizado: {item}", "success")
                else:
                    shutil.copy2(src, dst)
                    if log_callback: log_callback(f"📄 Copiado: {item}", "success")

            # ✅ OCULTAR ITEM NO WINDOWS (arquivo OU pasta)
            if sys.platform == "win32":
                import ctypes
                FILE_ATTRIBUTE_HIDDEN = 0x02
                ctypes.windll.kernel32.SetFileAttributesW(dst, FILE_ATTRIBUTE_HIDDEN)
                if log_callback: log_callback(f"👁️  Ocultado: {item}", "info")

            success_count += 1

        except Exception as e:
            failed_count += 1
            if log_callback: log_callback(f"❌ Falha ao copiar '{item}': {str(e)}", "error")

    # ✅ FINALIZAÇÃO
    if log_callback:
        log_callback(f"\n🎉 INSTALAÇÃO CONCLUÍDA!\n"
                     f"   ✔️ Sucesso: {success_count}\n"
                     f"   ⚠️ Ignorados (iguais): {skipped_count}\n"
                     f"   ❌ Falhas: {failed_count}", "success")

    return success_count > 0
