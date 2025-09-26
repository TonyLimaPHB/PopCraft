import os
from popstation_core import get_script_root, ensure_dir  # ✅ IMPORTA AS FUNÇÕES NECESSÁRIAS
from popstation_gui import PopsManagerGUI
from tkinterdnd2 import TkinterDnD

if __name__ == "__main__":
    # ✅ Garante que a pasta de logs exista
    ensure_dir("logs")
    log_file = os.path.join("logs", "popstation.log")
    if os.path.exists(log_file):
        open(log_file, "w", encoding="utf-8").close()

    # ✅ Obtém a pasta raiz do script
    script_root = get_script_root()
    print(f"[INFO] Pasta raiz do script: {script_root}")

    # ✅ Inicia a interface gráfica
    root = TkinterDnD.Tk()
    app = PopsManagerGUI(root)
    root.mainloop()
