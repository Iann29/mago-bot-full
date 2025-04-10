import tkinter as tk
from tkinter import ttk, messagebox
import os
import sys

# Adiciona a raiz do projeto ao PYTHONPATH para garantir importações corretas
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

from auth.supabase_auth import SupabaseAuth
from auth.config import SUPABASE_URL, SUPABASE_KEY

class LoginWindow:
    """
    Login window for the HayDay Bot application.
    Handles user authentication through Supabase.
    """
    
    def __init__(self, root, on_login_success=None):
        """
        Initialize the login window.
        
        Args:
            root: The Tkinter root window
            on_login_success: Callback function to run after successful login
        """
        self.root = root
        self.on_login_success = on_login_success
        
        # Initialize Supabase Auth
        self.auth_handler = SupabaseAuth(SUPABASE_URL, SUPABASE_KEY)
        
        # Set up the UI
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the login UI components."""
        # Configure the root window
        self.root.title("HayDay Bot - Login")
        self.root.geometry("400x300")
        self.root.resizable(False, False)
        
        # Main frame
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="HayDay Bot Login", font=("Helvetica", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # Username
        username_frame = ttk.Frame(main_frame)
        username_frame.pack(fill=tk.X, pady=5)
        
        username_label = ttk.Label(username_frame, text="Username:", width=10)
        username_label.pack(side=tk.LEFT, padx=(0, 5))
        
        self.username_var = tk.StringVar()
        username_entry = ttk.Entry(username_frame, textvariable=self.username_var)
        username_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Password
        password_frame = ttk.Frame(main_frame)
        password_frame.pack(fill=tk.X, pady=5)
        
        password_label = ttk.Label(password_frame, text="Password:", width=10)
        password_label.pack(side=tk.LEFT, padx=(0, 5))
        
        self.password_var = tk.StringVar()
        password_entry = ttk.Entry(password_frame, textvariable=self.password_var, show="*")
        password_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Remember credentials checkbox
        self.remember_var = tk.BooleanVar(value=False)
        remember_check = ttk.Checkbutton(main_frame, text="Lembrar credenciais", variable=self.remember_var)
        remember_check.pack(anchor=tk.W, pady=10)
        
        # Login button
        login_button = ttk.Button(main_frame, text="Login", command=self.login)
        login_button.pack(fill=tk.X, pady=10)
        
        # Status message
        self.status_var = tk.StringVar()
        status_label = ttk.Label(main_frame, textvariable=self.status_var, foreground="red")
        status_label.pack(pady=10)
        
        # Bind enter key to login
        self.root.bind("<Return>", lambda e: self.login())
        
        # Focus on username entry
        username_entry.focus()
    
    def login(self):
        """Attempt to login with the provided credentials."""
        username = self.username_var.get().strip()
        password = self.password_var.get().strip()
        
        if not username or not password:
            self.status_var.set("Por favor, preencha todos os campos")
            return
        
        # Show status
        self.status_var.set("Autenticando...")
        self.root.update()
        
        print(f"Tentando login com usuário: {username}")
        
        # Attempt login
        success, message, user_data = self.auth_handler.authenticate_user(username, password)
        
        print(f"Resultado: {success}, Mensagem: {message}")
        
        if success:
            # Save credentials if remember is checked
            if self.remember_var.get():
                self.save_credentials(username, password)
            
            # Call success callback if provided
            if self.on_login_success:
                self.on_login_success(user_data)
            else:
                print(f"Login bem-sucedido para {username}!")
                # Removendo o popup de confirmação
                self.root.destroy()
        else:
            print(f"Falha no login: {message}")
            self.status_var.set(message)
    
    def save_credentials(self, username, password):
        """Save the username and password for future sessions."""
        try:
            # Simple file-based credential storage with JSON
            # In a production environment, use a more secure approach like keyring or encrypted storage
            import json
            credentials = {"username": username, "password": password}
            with open(os.path.join(project_root, "auth", ".remembered_credentials"), "w") as f:
                json.dump(credentials, f)
        except Exception as e:
            print(f"Error saving credentials: {e}")
    
    def load_remembered_username(self):
        """Load the remembered username and password if available."""
        try:
            import json
            credential_file = os.path.join(project_root, "auth", ".remembered_credentials")
            if os.path.exists(credential_file):
                with open(credential_file, "r") as f:
                    credentials = json.load(f)
                    if credentials and "username" in credentials:
                        self.username_var.set(credentials["username"])
                        if "password" in credentials:
                            self.password_var.set(credentials["password"])
                            # Marcar a opção de lembrar credenciais
                            self.remember_var.set(True)
                        return True
        except Exception as e:
            print(f"Error loading credentials: {e}")
            # Verificar o arquivo no formato antigo como fallback
            try:
                old_credential_file = os.path.join(project_root, "auth", ".remembered_user")
                if os.path.exists(old_credential_file):
                    with open(old_credential_file, "r") as f:
                        username = f.read().strip()
                        if username:
                            self.username_var.set(username)
                            return True
            except Exception:
                pass
        
        return False


def start_login_window(on_login_success=None):
    """
    Start the login window and return the authenticated user data.
    
    Args:
        on_login_success: Callback function to run after successful login
        
    Returns:
        The authenticated user data if login was successful, None otherwise
    """
    root = tk.Tk()
    app = LoginWindow(root, on_login_success)
    
    # Load remembered username if available
    app.load_remembered_username()
    
    # Run the main loop
    root.mainloop()
    
    # Return the authenticated user
    return app.auth_handler.get_current_user()


if __name__ == "__main__":
    # Test the login window
    def on_success(user_data):
        print(f"Login successful! User data: {user_data}")
    
    user = start_login_window(on_success)
    if user:
        print(f"Got user data: {user}")
