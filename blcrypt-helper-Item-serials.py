import sys
import os
import subprocess
import random
from pathlib import Path
import tkinter as tk
from tkinter import messagebox

def show_popup(title, message, msg_type='info'):
    """Show a popup message using tkinter"""
    root = tk.Tk()
    root.withdraw()
    
    if msg_type == 'info':
        messagebox.showinfo(title, message)
    elif msg_type == 'error':
        messagebox.showerror(title, message)
    elif msg_type == 'warning':
        return messagebox.askyesno(title, message)
    
    root.destroy()

def show_overwrite_dialog(filepath):
    """Show dialog for file overwrite options"""
    root = tk.Tk()
    root.withdraw()
    
    result = None
    
    def on_overwrite():
        nonlocal result
        result = 'overwrite'
        root.quit()
    
    def on_rename():
        nonlocal result
        result = 'rename'
        root.quit()
    
    def on_cancel():
        nonlocal result
        result = 'cancel'
        root.quit()
    
    dialog = tk.Toplevel(root)
    dialog.title("File Exists")
    dialog.geometry("400x150")
    dialog.resizable(False, False)
    
    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
    y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
    dialog.geometry(f"+{x}+{y}")
    
    msg = tk.Label(dialog, text=f"WARNING: {os.path.basename(filepath)} already exists!", 
                   pady=20, font=("Arial", 10, "bold"))
    msg.pack()
    
    button_frame = tk.Frame(dialog)
    button_frame.pack(pady=10)
    
    tk.Button(button_frame, text="Overwrite", command=on_overwrite, width=10).pack(side=tk.LEFT, padx=5)
    tk.Button(button_frame, text="Rename", command=on_rename, width=10).pack(side=tk.LEFT, padx=5)
    tk.Button(button_frame, text="Cancel", command=on_cancel, width=10).pack(side=tk.LEFT, padx=5)
    
    dialog.protocol("WM_DELETE_WINDOW", on_cancel)
    dialog.focus_force()
    
    root.mainloop()
    root.destroy()
    
    return result

def get_steam_id():
    """Read STEAM ID from STEAMID.txt in script directory"""
    script_dir = Path(__file__).parent
    steamid_file = script_dir / "STEAMID.txt"
    
    if not steamid_file.exists():
        show_popup("Error", "STEAMID.txt not found in script directory", 'error')
        return None
    
    try:
        with open(steamid_file, 'r') as f:
            steam_id = f.read().strip()
            if not steam_id:
                show_popup("Error", "STEAMID.txt is empty", 'error')
                return None
            return steam_id
    except Exception as e:
        show_popup("Error", f"Failed to read STEAMID.txt: {str(e)}", 'error')
        return None

def generate_unique_filename(base_path, extension):
    """Generate a unique filename with random number"""
    directory = base_path.parent
    base_name = base_path.stem
    
    while True:
        random_num = random.randint(1000, 9999)
        new_filename = directory / f"{base_name}_{random_num}{extension}"
        if not new_filename.exists():
            return new_filename

def run_blcrypt(command, input_file, output_file, steam_id, extra_args=None):
    """Run the blcrypt.py command with optional extra arguments"""
    script_dir = Path(__file__).parent
    blcrypt_path = script_dir / "blcrypt.py"
    
    if not blcrypt_path.exists():
        show_popup("Error", "blcrypt.py not found in script directory", 'error')
        return False
    
    cmd = [
        sys.executable, 
        str(blcrypt_path),
        command,
        "-in", str(input_file),
        "-out", str(output_file),
        "-id", steam_id
    ]
    
    # Add extra arguments if provided
    if extra_args:
        cmd.extend(extra_args)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return True
        else:
            error_msg = result.stderr if result.stderr else "Unknown error occurred"
            show_popup("Error", f"Command failed: {error_msg}", 'error')
            return False
    except Exception as e:
        show_popup("Error", f"Failed to run command: {str(e)}", 'error')
        return False

def main():
    if len(sys.argv) < 2:
        show_popup("Error", "Please drag and drop a .yaml or .sav file onto this script", 'error')
        sys.exit(1)
    
    input_file = Path(sys.argv[1])
    
    if not input_file.exists():
        show_popup("Error", f"File not found: {input_file}", 'error')
        sys.exit(1)
    
    steam_id = get_steam_id()
    if not steam_id:
        sys.exit(1)
    
    extension = input_file.suffix.lower()
    
    if extension == '.yaml':
        output_file = input_file.with_suffix('.sav')
        
        if output_file.exists():
            choice = show_overwrite_dialog(output_file)
            
            if choice == 'cancel':
                print("Operation cancelled")
                sys.exit(0)
            elif choice == 'rename':
                output_file = generate_unique_filename(input_file.with_suffix(''), '.sav')
                print(f"Saving as: {output_file}")
        
        print("Running encryption...")
        if run_blcrypt('encrypt', input_file, output_file, steam_id, ['--encode-serials']):
            show_popup("Success", f"Successfully written to {output_file.name}", 'info')
        
    elif extension == '.sav':
        output_file = input_file.with_suffix('.yaml')
        
        print("Running decryption...")
        if run_blcrypt('decrypt', input_file, output_file, steam_id, ['--decode-serials']):
            show_popup("Success", f"Successfully written to {output_file.name}", 'info')
        
    else:
        show_popup("Error", "Invalid file type. Only .yaml and .sav files are supported.", 'error')
        sys.exit(1)

if __name__ == "__main__":
    main()