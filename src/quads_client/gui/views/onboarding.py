"""Onboarding wizard for first-time setup"""

import tkinter as tk
from tkinter import ttk, messagebox


class OnboardingWizard(tk.Toplevel):
    """Multi-step onboarding wizard for new users"""

    def __init__(self, parent, shell):
        super().__init__(parent)
        self.parent = parent
        self.shell = shell

        self.title("Welcome to QUADS Client")
        self.geometry("600x520")
        self.resizable(False, False)

        self.current_step = 0
        self.server_data = {}

        self.transient(parent)
        self.grab_set()

        # Apply theme colors
        if hasattr(parent, "theme_manager"):
            parent.theme_manager.configure_toplevel(self)

        self._create_ui()
        self._show_step(0)

    def _create_ui(self):
        """Create the wizard UI"""
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        self.content_frame = ttk.Frame(main_frame)
        self.content_frame.pack(fill=tk.BOTH, expand=True)

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))

        self.back_button = ttk.Button(button_frame, text="Back", command=self._previous_step)
        self.back_button.pack(side=tk.LEFT)

        self.skip_button = ttk.Button(button_frame, text="Skip Setup", command=self._skip_setup)
        self.skip_button.pack(side=tk.LEFT, padx=10)

        self.next_button = ttk.Button(button_frame, text="Next", command=self._next_step)
        self.next_button.pack(side=tk.RIGHT)

    def _show_step(self, step):
        """Show a specific wizard step"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        self.current_step = step

        if step == 0:
            self._show_welcome()
        elif step == 1:
            self._show_add_server()
        elif step == 2:
            self._show_connect_register()
        elif step == 3:
            self._show_done()

        self.back_button.config(state=tk.NORMAL if step > 0 else tk.DISABLED)
        self.skip_button.config(state=tk.NORMAL if step < 3 else tk.DISABLED)

        if step == 3:
            self.next_button.config(text="Get Started", command=self._finish)
        else:
            self.next_button.config(text="Next", command=self._next_step)

    def _show_welcome(self):
        """Show welcome screen"""
        title = ttk.Label(
            self.content_frame,
            text="Welcome to QUADS Client!",
            font=("TkDefaultFont", 16, "bold"),
        )
        title.pack(pady=30)

        message = ttk.Label(
            self.content_frame,
            text="This wizard will help you set up your first QUADS server connection.\n\n"
            "You'll be able to:\n"
            "  • Add your QUADS server\n"
            "  • Connect and authenticate\n"
            "  • Start scheduling hosts\n\n"
            "Click Next to continue or Skip Setup to configure manually later.",
            justify=tk.CENTER,
        )
        message.pack(pady=20)

    def _show_add_server(self):
        """Show add server screen"""
        title = ttk.Label(
            self.content_frame,
            text="Add Your First Server",
            font=("TkDefaultFont", 14, "bold"),
        )
        title.pack(pady=(10, 5))

        form_frame = ttk.Frame(self.content_frame)
        form_frame.pack(pady=10, padx=40, fill=tk.BOTH)

        ttk.Label(form_frame, text="Server Name:").grid(row=0, column=0, sticky=tk.W, pady=8)
        self.server_name_entry = ttk.Entry(form_frame, width=30)
        self.server_name_entry.grid(row=0, column=1, pady=8, padx=10)
        self.server_name_entry.insert(0, "my-quads")

        ttk.Label(form_frame, text="Server URL:").grid(row=1, column=0, sticky=tk.W, pady=8)
        self.server_url_entry = ttk.Entry(form_frame, width=30)
        self.server_url_entry.grid(row=1, column=1, pady=8, padx=10)
        self.server_url_entry.insert(0, "https://")

        self.verify_ssl_var = tk.BooleanVar(value=True)
        ssl_check = ttk.Checkbutton(form_frame, text="Verify SSL certificate", variable=self.verify_ssl_var)
        ssl_check.grid(row=2, column=1, sticky=tk.W, pady=8)

        hint_label = ttk.Label(
            self.content_frame,
            text="Tip: You can add more servers later from the Servers view.",
            font=("TkDefaultFont", 8),
        )
        hint_label.pack(pady=(5, 10))

    def _show_connect_register(self):
        """Show connect/register screen"""
        title = ttk.Label(
            self.content_frame,
            text=f"Connect to {self.server_data.get('name', 'Server')}",
            font=("TkDefaultFont", 14, "bold"),
        )
        title.pack(pady=20)

        notebook = ttk.Notebook(self.content_frame)
        notebook.pack(fill=tk.BOTH, expand=True, padx=40, pady=10)

        # SSO Token tab (preferred)
        token_frame = ttk.Frame(notebook, padding=20)
        notebook.add(token_frame, text="SSO Token")

        ttk.Label(token_frame, text="Email:").grid(row=0, column=0, sticky=tk.W, pady=10)
        self.token_email_entry = ttk.Entry(token_frame, width=30)
        self.token_email_entry.grid(row=0, column=1, pady=10, padx=10)

        ttk.Label(token_frame, text="SSO Token:").grid(row=1, column=0, sticky=tk.W, pady=10)
        self.token_entry = ttk.Entry(token_frame, width=30, show="*")
        self.token_entry.grid(row=1, column=1, pady=10, padx=10)

        ttk.Button(token_frame, text="Connect", command=self._do_token_login).grid(
            row=2, column=1, pady=20, sticky=tk.E
        )

        token_tip = ttk.Label(
            token_frame,
            text="Get your token from the QUADS web portal under Profile > API Tokens.",
            font=("TkDefaultFont", 9),
            foreground="gray",
            wraplength=350,
        )
        token_tip.grid(row=3, column=0, columnspan=2, pady=(10, 0), sticky=tk.W)

        # Login tab
        login_frame = ttk.Frame(notebook, padding=20)
        notebook.add(login_frame, text="Login")

        ttk.Label(login_frame, text="Email:").grid(row=0, column=0, sticky=tk.W, pady=10)
        self.login_email_entry = ttk.Entry(login_frame, width=30)
        self.login_email_entry.grid(row=0, column=1, pady=10, padx=10)

        ttk.Label(login_frame, text="Password:").grid(row=1, column=0, sticky=tk.W, pady=10)
        self.login_password_entry = ttk.Entry(login_frame, width=30, show="*")
        self.login_password_entry.grid(row=1, column=1, pady=10, padx=10)

        ttk.Button(login_frame, text="Login", command=self._do_login).grid(row=2, column=1, pady=20, sticky=tk.E)

        login_tip = ttk.Label(
            login_frame,
            text="For legacy username/password authentication.",
            font=("TkDefaultFont", 9),
            foreground="gray",
            wraplength=350,
        )
        login_tip.grid(row=3, column=0, columnspan=2, pady=(10, 0), sticky=tk.W)

        # Register tab
        register_frame = ttk.Frame(notebook, padding=20)
        notebook.add(register_frame, text="Register")

        ttk.Label(register_frame, text="Email:").grid(row=0, column=0, sticky=tk.W, pady=10)
        self.register_email_entry = ttk.Entry(register_frame, width=30)
        self.register_email_entry.grid(row=0, column=1, pady=10, padx=10)

        ttk.Label(register_frame, text="Password:").grid(row=1, column=0, sticky=tk.W, pady=10)
        self.register_password_entry = ttk.Entry(register_frame, width=30, show="*")
        self.register_password_entry.grid(row=1, column=1, pady=10, padx=10)

        ttk.Label(register_frame, text="Confirm:").grid(row=2, column=0, sticky=tk.W, pady=10)
        self.register_confirm_entry = ttk.Entry(register_frame, width=30, show="*")
        self.register_confirm_entry.grid(row=2, column=1, pady=10, padx=10)

        ttk.Button(register_frame, text="Register", command=self._do_register).grid(
            row=3, column=1, pady=20, sticky=tk.E
        )

        register_tip = ttk.Label(
            register_frame,
            text="Create a new account with email and password.",
            font=("TkDefaultFont", 9),
            foreground="gray",
            wraplength=350,
        )
        register_tip.grid(row=4, column=0, columnspan=2, pady=(10, 0), sticky=tk.W)

        self.status_label = ttk.Label(
            self.content_frame, text="", foreground=self.parent.theme_manager.get_color("accent")
        )
        self.status_label.pack(pady=(5, 10))

    def _show_done(self):
        """Show completion screen"""
        title = ttk.Label(
            self.content_frame,
            text="You're All Set!",
            font=("TkDefaultFont", 16, "bold"),
        )
        title.pack(pady=30)

        status = "✓ Server configured\n"
        if self.shell.is_authenticated():
            user = self.shell.connection.username if self.shell.connection else "user"
            status += f"✓ Logged in as {user}\n"
        else:
            status += "○ Not logged in (you can login later)\n"

        status_label = ttk.Label(
            self.content_frame,
            text=status,
            font=("TkDefaultFont", 12),
            justify=tk.CENTER,
        )
        status_label.pack(pady=20)

        message = ttk.Label(
            self.content_frame,
            text="You can now start scheduling hosts.\n" "Click 'Get Started' to begin using QUADS Client.",
            justify=tk.CENTER,
        )
        message.pack(pady=20)

    def _next_step(self):
        """Move to next step"""
        if self.current_step == 1:
            if not self._validate_server():
                return

        self._show_step(self.current_step + 1)

    def _previous_step(self):
        """Move to previous step"""
        if self.current_step > 0:
            self._show_step(self.current_step - 1)

    def _validate_server(self):
        """Validate and save server data"""
        name = self.server_name_entry.get().strip()
        url = self.server_url_entry.get().strip()

        if not name:
            messagebox.showerror("Error", "Server name is required")
            return False

        if not url or not url.startswith("http"):
            messagebox.showerror("Error", "Valid server URL is required (must start with http:// or https://)")
            return False

        self.server_data = {
            "name": name,
            "url": url,
            "verify": self.verify_ssl_var.get(),
        }

        try:
            # Use programmatic server add method (DRY - reuses CLI logic)
            success, message, version = self.shell.server_commands.add_server_programmatic(
                name=name,
                url=url,
                username="",  # Empty triggers registration mode
                password="",  # Empty triggers registration mode
                verify=self.verify_ssl_var.get(),
                test_connection=True,
            )

            if not success:
                messagebox.showerror("Error", message)
                return False

            # Connect to server (with session dedup and zombie cleanup)
            success_conn, error = self.shell.connect_to_server(name)
            if not success_conn:
                messagebox.showwarning("Connection", f"Server added but could not connect: {error}")

        except Exception as e:
            import traceback

            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to add server: {e}")
            return False

        return True

    def _do_login(self):
        """Perform login"""
        email = self.login_email_entry.get().strip()
        password = self.login_password_entry.get()

        if not email or not password:
            self.status_label.config(
                text="Email and password required", foreground=self.parent.theme_manager.get_color("error")
            )
            return

        try:
            self.status_label.config(text="Logging in...", foreground=self.parent.theme_manager.get_color("accent"))
            self.update()

            # Use programmatic login method (DRY - reuses CLI logic)
            success, message, role = self.shell.user_commands.login_programmatic(email, password)

            if success:
                # Update credentials in config for future use
                server_name = self.shell.connection.current_server
                if server_name:
                    try:
                        self.shell.config.update_server_credentials(server_name, email, password)
                    except Exception:
                        pass  # Non-critical if this fails

                self.status_label.config(
                    text="✓ Login successful!", foreground=self.parent.theme_manager.get_color("success")
                )
                self.next_button.config(state=tk.NORMAL)

                # Update parent GUI status bar and connection indicator
                if hasattr(self.parent, "update_status"):
                    server_name = self.shell.connection.current_server
                    username = self.shell.connection.username
                    self.parent.update_status(f"Connected to {server_name} as {username}")
                if hasattr(self.parent, "update_role_visibility"):
                    self.parent.update_role_visibility()

                self.after(1500, lambda: self._show_step(3))
            else:
                self.status_label.config(
                    text=f"Login failed: {message}", foreground=self.parent.theme_manager.get_color("error")
                )
        except Exception as e:
            self.status_label.config(
                text=f"Login failed: {e}", foreground=self.parent.theme_manager.get_color("error")
            )

    def _do_register(self):
        """Perform registration"""
        email = self.register_email_entry.get().strip()
        password = self.register_password_entry.get()
        confirm = self.register_confirm_entry.get()

        if not email or not password:
            self.status_label.config(
                text="Email and password required", foreground=self.parent.theme_manager.get_color("error")
            )
            messagebox.showerror("Validation Error", "Email and password are required")
            return

        # Basic email validation
        if "@" not in email or "." not in email:
            self.status_label.config(
                text="Invalid email format", foreground=self.parent.theme_manager.get_color("error")
            )
            messagebox.showerror(
                "Invalid Email", "Please enter a valid email address.\n\n" "Example: user@example.com"
            )
            return

        if len(password) < 6:
            self.status_label.config(
                text="Password too short", foreground=self.parent.theme_manager.get_color("error")
            )
            messagebox.showerror(
                "Password Too Short",
                "Password must be at least 6 characters long.\n\n" "Please choose a stronger password.",
            )
            return

        if password != confirm:
            self.status_label.config(
                text="Passwords don't match", foreground=self.parent.theme_manager.get_color("error")
            )
            messagebox.showerror(
                "Password Mismatch",
                "The passwords you entered do not match.\n\n"
                "Please ensure both password fields contain the same password.",
            )
            # Clear confirm field to re-enter
            self.register_confirm_entry.delete(0, tk.END)
            self.register_confirm_entry.focus()
            return

        try:
            self.status_label.config(text="Registering...", foreground=self.parent.theme_manager.get_color("accent"))
            self.update()

            # Capture output to check for success
            self.shell._capture_output = True
            self.shell._captured_messages = []

            self.shell.user_commands.cmd_register(f"{email} {password}")

            self.shell._capture_output = False

            # Check if registration was successful by looking at captured messages
            success = False
            already_exists = False
            registration_disabled = False
            for level, msg in self.shell._captured_messages:
                if "OK: User registered successfully" in msg or "OK: Logged in successfully" in msg:
                    success = True
                elif "already exists" in msg.lower():
                    already_exists = True
                elif "registration is disabled" in msg.lower():
                    registration_disabled = True

            if registration_disabled:
                self.status_label.config(
                    text="Registration disabled - use SSO Token tab",
                    foreground=self.parent.theme_manager.get_color("warning"),
                )
                messagebox.showinfo(
                    "Registration Disabled",
                    "This server requires SSO authentication.\n\n"
                    "Please use the 'SSO Token' tab to authenticate with\n"
                    "a token from the QUADS web portal.",
                )
                return

            if already_exists:
                self.status_label.config(
                    text="Email already registered - please login instead",
                    foreground=self.parent.theme_manager.get_color("warning"),
                )
                messagebox.showwarning(
                    "Already Registered",
                    "This email address is already registered.\n\n"
                    "Please use the Login tab to sign in with your existing account.",
                )
                return

            if success and self.shell.is_authenticated():
                self.status_label.config(
                    text="✓ Registration and login successful!",
                    foreground=self.parent.theme_manager.get_color("success"),
                )
                self.next_button.config(state=tk.NORMAL)

                # Update parent GUI status bar and connection indicator
                if hasattr(self.parent, "update_status"):
                    server_name = self.shell.connection.current_server
                    username = self.shell.connection.username
                    self.parent.update_status(f"Connected to {server_name} as {username}")
                if hasattr(self.parent, "update_role_visibility"):
                    self.parent.update_role_visibility()

                self.after(1500, lambda: self._show_step(3))
            elif success:
                # Registered but not logged in - use programmatic login (DRY)
                self.status_label.config(
                    text="Registration successful, logging in...",
                    foreground=self.parent.theme_manager.get_color("accent"),
                )
                self.update()

                try:
                    login_success, login_message, role = self.shell.user_commands.login_programmatic(email, password)

                    if login_success:
                        # Save credentials to config
                        server_name = self.shell.connection.current_server
                        if server_name:
                            try:
                                self.shell.config.update_server_credentials(server_name, email, password)
                            except Exception:
                                pass

                        self.status_label.config(
                            text="✓ Registration and login successful!",
                            foreground=self.parent.theme_manager.get_color("success"),
                        )
                        self.next_button.config(state=tk.NORMAL)

                        # Update parent GUI status bar and connection indicator
                        if hasattr(self.parent, "update_status"):
                            server_name = self.shell.connection.current_server
                            username = self.shell.connection.username
                            self.parent.update_status(f"Connected to {server_name} as {username}")
                        if hasattr(self.parent, "update_role_visibility"):
                            self.parent.update_role_visibility()

                        self.after(1500, lambda: self._show_step(3))
                    else:
                        self.status_label.config(
                            text="Registered - please login manually",
                            foreground=self.parent.theme_manager.get_color("warning"),
                        )
                        messagebox.showinfo(
                            "Registration Successful",
                            "Your account has been created successfully!\n\n"
                            "Please click the 'Login' tab above and sign in with your new credentials.",
                        )
                except Exception:
                    self.status_label.config(
                        text="Registered - please login manually",
                        foreground=self.parent.theme_manager.get_color("warning"),
                    )
                    messagebox.showinfo(
                        "Registration Successful",
                        "Your account has been created successfully!\n\n"
                        "Please click the 'Login' tab above and sign in with your new credentials.",
                    )
            else:
                self.status_label.config(
                    text="Registration may have failed - check messages",
                    foreground=self.parent.theme_manager.get_color("warning"),
                )
        except Exception as e:
            self.shell._capture_output = False
            self.status_label.config(
                text=f"Registration failed: {e}", foreground=self.parent.theme_manager.get_color("error")
            )
            messagebox.showerror("Registration Failed", str(e))

    def _do_token_login(self):
        """Perform SSO token login"""
        email = self.token_email_entry.get().strip()
        token = self.token_entry.get().strip()

        if not email or not token:
            self.status_label.config(
                text="Email and token required", foreground=self.parent.theme_manager.get_color("error")
            )
            return

        if not token.startswith("qat_"):
            self.status_label.config(
                text="Invalid token format (must start with qat_)",
                foreground=self.parent.theme_manager.get_color("error"),
            )
            return

        try:
            self.status_label.config(
                text="Authenticating...", foreground=self.parent.theme_manager.get_color("accent")
            )
            self.update()

            success, message, role = self.shell.user_commands.token_login_programmatic(email, token)

            if success:
                server_name = self.shell.connection.current_server
                if server_name:
                    try:
                        self.shell.config.update_server_api_token(server_name, email, token)
                    except Exception:
                        pass

                self.status_label.config(
                    text="✓ Token authentication successful!",
                    foreground=self.parent.theme_manager.get_color("success"),
                )
                self.next_button.config(state=tk.NORMAL)

                if hasattr(self.parent, "update_status"):
                    server_name = self.shell.connection.current_server
                    username = self.shell.connection.username
                    self.parent.update_status(f"Connected to {server_name} as {username}")
                if hasattr(self.parent, "update_role_visibility"):
                    self.parent.update_role_visibility()

                self.after(1500, lambda: self._show_step(3))
            else:
                self.status_label.config(
                    text=f"Authentication failed: {message}",
                    foreground=self.parent.theme_manager.get_color("error"),
                )
        except Exception as e:
            self.status_label.config(
                text=f"Authentication failed: {e}", foreground=self.parent.theme_manager.get_color("error")
            )

    def _skip_setup(self):
        """Skip the setup wizard"""
        if messagebox.askyesno(
            "Skip Setup",
            "Are you sure you want to skip the setup wizard?\n\n"
            "You can configure servers later from the Servers view.",
        ):
            self.destroy()

    def _finish(self):
        """Finish the wizard"""
        # Update parent GUI status one more time before closing
        if hasattr(self.parent, "update_status") and hasattr(self.parent, "update_role_visibility"):
            if self.shell.is_authenticated():
                server_name = self.shell.connection.current_server
                username = self.shell.connection.username
                self.parent.update_status(f"Connected to {server_name} as {username}")
            else:
                self.parent.update_status("Not connected")
            self.parent.update_role_visibility()

        self.destroy()
