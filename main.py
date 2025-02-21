import os
import sys
import json
import subprocess
from pathlib import Path
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton,
                             QFileDialog, QGroupBox, QCheckBox, QLineEdit, QMessageBox, QProgressBar,
                             QTextEdit, QScrollBar)
from PyQt5.QtCore import Qt, QProcess

class ROSUESetupGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        # Add completion states
        self.steps_completed = {
            "plugins": False,
            "update": False,
            "compile": False
        }
        self.unreal_engine_path = None
        self.selected_project = None
        self.setWindowTitle("ROSUE Simulator Setup")
        self.setGeometry(100, 100, 800, 600)
        
        self.main_widget = QWidget()
        self.layout = QVBoxLayout()
        
        # Unreal Engine Detection Section
        self.engine_group = QGroupBox("Step 1: Unreal Engine 5 Detection")
        self.engine_layout = QVBoxLayout()
        self.engine_status = QLabel("Searching for Unreal Engine 5...")
        self.engine_path_edit = QLineEdit()
        self.engine_path_edit.setReadOnly(True)
        self.browse_engine_btn = QPushButton("Browse Manually")
        self.browse_engine_btn.clicked.connect(self.browse_engine)
        self.engine_layout.addWidget(self.engine_status)
        self.engine_layout.addWidget(self.engine_path_edit)
        self.engine_layout.addWidget(self.browse_engine_btn)
        self.engine_group.setLayout(self.engine_layout)
        
        # Project Selection Section
        self.project_group = QGroupBox("Step 2: Select Unreal Project")
        self.project_group.setEnabled(False)
        self.project_layout = QVBoxLayout()
        self.project_status = QLabel("No project selected")
        self.browse_project_btn = QPushButton("Browse Project")
        self.browse_project_btn.clicked.connect(self.browse_project)
        self.validation_list = QCheckBox("Project path contains no spaces")
        self.cpp_support_check = QCheckBox("Project has C++ support")
        self.validation_list.setEnabled(False)
        self.cpp_support_check.setEnabled(False)
        self.project_path_edit = QLineEdit()
        self.project_path_edit.setReadOnly(True)
        self.project_layout.addWidget(self.project_status)
        self.project_layout.addWidget(self.project_path_edit)
        self.project_layout.addWidget(self.browse_project_btn)
        self.project_layout.addWidget(self.validation_list)
        self.project_layout.addWidget(self.cpp_support_check)
        self.project_group.setLayout(self.project_layout)

        # Add Log Section
        self.log_group = QGroupBox("Installation Log")
        self.log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(200)
        self.log_layout.addWidget(self.log_text)
        self.log_group.setLayout(self.log_layout)

        # Progress Section with separate buttons
        self.progress_bar = QProgressBar()
        self.button_layout = QVBoxLayout()
        
        # Add remove plugins button
        self.remove_plugins_btn = QPushButton("Remove ROSUE Plugins")
        self.remove_plugins_btn.clicked.connect(self.remove_plugins)
        self.remove_plugins_btn.setEnabled(False)
        
        self.install_plugins_btn = QPushButton("1. Install Plugins")
        self.install_plugins_btn.clicked.connect(lambda: self.start_step("plugins"))
        self.update_project_btn = QPushButton("2. Update Project File")
        self.update_project_btn.clicked.connect(lambda: self.start_step("update"))
        self.compile_btn = QPushButton("3. Compile Project")
        self.compile_btn.clicked.connect(lambda: self.start_step("compile"))
        
        self.steps_buttons = {
            "plugins": self.install_plugins_btn,
            "update": self.update_project_btn,
            "compile": self.compile_btn
        }
        
        # Add cache removal checkbox
        self.clear_cache_cb = QCheckBox("Clear cache before compilation (recommended for clean rebuild)")
        self.clear_cache_cb.setChecked(False)
        self.button_layout.addWidget(self.clear_cache_cb)
        
        for btn in [self.install_plugins_btn, self.update_project_btn, self.compile_btn]:
            btn.setEnabled(False)
            self.button_layout.addWidget(btn)
            
        # Add remove button at the bottom
        separator = QLabel("─" * 50)  # Visual separator
        separator.setAlignment(Qt.AlignCenter)
        self.button_layout.addWidget(separator)
        self.button_layout.addWidget(self.remove_plugins_btn)

        self.layout.addWidget(self.engine_group)
        self.layout.addWidget(self.project_group)
        self.layout.addWidget(self.log_group)
        self.layout.addWidget(self.progress_bar)
        
        button_widget = QWidget()
        button_widget.setLayout(self.button_layout)
        self.layout.addWidget(button_widget)
        
        self.main_widget.setLayout(self.layout)
        self.setCentralWidget(self.main_widget)
        
        self.detect_unreal_engine()

        # Add process handler
        self.process = QProcess()
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.finished.connect(self.process_finished)

    def detect_unreal_engine(self):
        search_paths = [
            "/opt/UnrealEngine",
            "/opt/unreal-engine",
            os.path.expanduser("~/UnrealEngine"),
            "/opt/UE5",
            "/opt/UnrealEngine5"
        ]
        
        for path in search_paths:
            if os.path.exists(os.path.join(path, "Engine/Build/BatchFiles/Linux/Build.sh")):
                self.unreal_engine_path = path
                break
        
        if self.unreal_engine_path:
            self.engine_status.setText("Unreal Engine 5 found at:")
            self.engine_path_edit.setText(self.unreal_engine_path)
            self.project_group.setEnabled(True)
        else:
            self.engine_status.setText("Unreal Engine 5 not found automatically")

    def browse_engine(self):
        path = QFileDialog.getExistingDirectory(self, "Select Unreal Engine Root Directory")
        if path:
            build_sh = os.path.join(path, "Engine/Build/BatchFiles/Linux/Build.sh")
            if os.path.exists(build_sh):
                self.unreal_engine_path = path
                self.engine_path_edit.setText(path)
                self.project_group.setEnabled(True)
            else:
                QMessageBox.warning(self, "Invalid Directory", "Selected directory is not a valid Unreal Engine installation")

    def browse_project(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Unreal Project", "", "Unreal Projects (*.uproject)")
        if path:
            self.selected_project = path
            self.project_path_edit.setText(path)
            # Reset completion status when new project is selected
            for step in self.steps_completed:
                self.update_button_text(step, False)
            self.validate_project_path(path)
            self.install_plugins_btn.setEnabled(self.validation_list.isChecked())
            self.update_project_btn.setEnabled(self.validation_list.isChecked())
            self.compile_btn.setEnabled(self.validation_list.isChecked())

    def check_cpp_support(self, project_path):
        """Check if the project has C++ support"""
        try:
            with open(project_path, 'r') as f:
                project_data = json.load(f)
            
            project_name = os.path.basename(project_path).replace('.uproject', '')
            
            # Check for Modules section and matching module name
            if "Modules" in project_data:
                for module in project_data["Modules"]:
                    if module.get("Name") == project_name:
                        self.log_message("C++ support detected in project")
                        return True
            
            self.log_message("No C++ support detected in project", error=True)
            return False
        except Exception as e:
            self.log_message(f"Error checking C++ support: {str(e)}", error=True)
            return False

    def validate_project_path(self, path):
        has_spaces = ' ' in path
        cpp_support = self.check_cpp_support(path)
        
        self.validation_list.setChecked(not has_spaces)
        self.cpp_support_check.setChecked(cpp_support)
        
        if has_spaces:
            QMessageBox.warning(self, "Path Error", "Project path contains spaces which may cause compilation issues!")
        
        if not cpp_support:
            QMessageBox.warning(self, "Project Error", 
                "This appears to be a Blueprint-only project. C++ support is required.\n"
                "Please convert your project to C++ by adding a C++ class in Unreal Editor first.")
        
        # Enable buttons only if all checks pass
        buttons_enabled = not has_spaces and cpp_support
        self.install_plugins_btn.setEnabled(buttons_enabled)
        self.update_project_btn.setEnabled(buttons_enabled)
        self.compile_btn.setEnabled(buttons_enabled)
        self.remove_plugins_btn.setEnabled(buttons_enabled)

    def update_button_text(self, step, completed=False):
        """Update button text with checkmark if completed"""
        button = self.steps_buttons[step]
        base_text = button.text().split(" ✓")[0]  # Remove existing checkmark if any
        button.setText(f"{base_text} ✓" if completed else base_text)
        self.steps_completed[step] = completed

    def start_step(self, step):
        if not all([self.unreal_engine_path, self.selected_project]):
            return

        try:
            if step == "plugins":
                self.progress_bar.setValue(10)
                self.install_plugins()
                self.update_button_text("plugins", True)
            elif step == "update":
                self.progress_bar.setValue(40)
                self.update_uproject_file()
                self.update_button_text("update", True)
            elif step == "compile":
                self.progress_bar.setValue(60)
                self.compile_project()
                # Compile completion is handled in process_finished
        except Exception as e:
            self.log_message(f"Error during {step}: {str(e)}", error=True)
            self.progress_bar.setValue(0)
            self.update_button_text(step, False)

    def log_message(self, message, error=False):
        self.log_text.append(f"{'[ERROR] ' if error else ''}{message}")
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )

    def handle_stdout(self):
        data = self.process.readAllStandardOutput().data().decode()
        self.log_message(data)

    def handle_stderr(self):
        data = self.process.readAllStandardError().data().decode()
        self.log_message(data, error=True)

    def start_installation(self):
        if not all([self.unreal_engine_path, self.selected_project]):
            return

        try:
            self.progress_bar.setValue(10)
            self.install_plugins()
            self.progress_bar.setValue(50)
            self.update_uproject_file()
            self.progress_bar.setValue(70)
            self.compile_project()
            self.progress_bar.setValue(100)
            QMessageBox.information(self, "Success", "Installation completed successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Installation failed: {str(e)}")
            self.progress_bar.setValue(0)

    def install_plugins(self):
        self.log_message("Starting plugin installation...")
        project_path = os.path.dirname(self.selected_project)
        plugins_dir = os.path.join(project_path, "Plugins")
        os.makedirs(plugins_dir, exist_ok=True)
        
        repos = [
            ("https://github.com/mistrjirka/MetaLidar.git", "MetaLidar"),
            ("https://gitlab.fel.cvut.cz/svitijir/roscontrol.git", "roscontrol"),
            ("https://github.com/mistrjirka/MathToolkit.git", "MathToolkit")
        ]
        
        existing_plugins = []
        for _, name in repos:
            if os.path.exists(os.path.join(plugins_dir, name)):
                existing_plugins.append(name)
        
        if existing_plugins:
            reply = QMessageBox.question(self, 'Plugins Already Exist',
                f"The following plugins are already installed:\n{', '.join(existing_plugins)}\n\n"
                "Do you want to delete and reinstall them with the latest version?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                for name in existing_plugins:
                    import shutil
                    self.log_message(f"Removing existing plugin: {name}")
                    shutil.rmtree(os.path.join(plugins_dir, name))
            else:
                self.log_message("Plugin installation skipped by user")
                return
        
        for url, name in repos:
            target_dir = os.path.join(plugins_dir, name)
            if not os.path.exists(target_dir):
                self.log_message(f"Cloning {name}...")
                process = subprocess.run(["git", "clone", url, target_dir], 
                                      capture_output=True, text=True)
                self.log_message(process.stdout)
                if process.returncode != 0:
                    self.log_message(process.stderr, error=True)
                    raise Exception(f"Failed to clone {name}")

        self.log_message("Plugin installation completed successfully!")
        self.progress_bar.setValue(30)

    def update_uproject_file(self):
        self.log_message("Updating project file...")
        required_plugins = {"MetaLidar", "roscontrol", "MathToolkit"}
        
        with open(self.selected_project, 'r') as f:
            project_data = json.load(f)
        
        # Initialize Plugins array if it doesn't exist
        if "Plugins" not in project_data:
            project_data["Plugins"] = []
            
        # Get existing plugins and remove any duplicates of our plugins
        existing_plugins = project_data["Plugins"]
        project_data["Plugins"] = [p for p in existing_plugins 
                                 if p["Name"] not in required_plugins]
        
        # Add our plugins if they're not already there
        for plugin in required_plugins:
            plugin_entry = {
                "Name": plugin,
                "Enabled": True
            }
            project_data["Plugins"].append(plugin_entry)
            self.log_message(f"Added/Updated plugin: {plugin}")
        
        with open(self.selected_project, 'w') as f:
            json.dump(project_data, f, indent=4)
        self.log_message("Project file updated successfully!")
        self.progress_bar.setValue(50)

    def clear_project_cache(self, project_dir):
        """Clear all cache directories in the project"""
        self.log_message("Clearing project cache...")
        import subprocess
        
        cmd = [
            'find', project_dir,
            '-type', 'd',
            '(',
            '-name', 'Binaries',
            '-o', '-name', 'Intermediate',
            '-o', '-name', 'Saved',
            '-o', '-name', 'DerivedDataCache',
            ')',
            '-exec', 'rm', '-rf', '{}', '+'
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                self.log_message("Cache cleared successfully")
            else:
                self.log_message(f"Error clearing cache: {result.stderr}", error=True)
        except Exception as e:
            self.log_message(f"Failed to clear cache: {str(e)}", error=True)

    def compile_project(self):
        self.log_message("Starting project compilation...")
        project_dir = os.path.dirname(self.selected_project)
        
        # Clear cache if option is selected
        if self.clear_cache_cb.isChecked():
            self.clear_project_cache(project_dir)
        
        project_name = os.path.basename(self.selected_project).replace('.uproject', '')
        build_script = "/opt/unreal-engine/Engine/Build/BatchFiles/Linux/Build.sh"
        
        if not os.path.exists(build_script):
            self.log_message(f"Build script not found at: {build_script}", error=True)
            build_script = os.path.join(self.unreal_engine_path, "Engine/Build/BatchFiles/Linux/Build.sh")
            self.log_message(f"Falling back to: {build_script}")
            
            if not os.path.exists(build_script):
                raise Exception("Could not find Build.sh script!")
        
        command = [
            build_script,
            f"{project_name}Editor",
            "Linux",
            "Development",
            f"-Project={self.selected_project}"  # Removed extra quotes that could cause issues
        ]
        
        self.log_message(f"Running command: {' '.join(command)}")
        
        # Ensure build script is executable
        os.chmod(build_script, 0o755)
        
        # Set working directory to UE directory to ensure proper build context
        self.process.setWorkingDirectory(os.path.dirname(os.path.dirname(os.path.dirname(build_script))))
        self.process.start(command[0], command[1:])

    def process_finished(self, exit_code, exit_status):
        if exit_code == 0:
            self.log_message("Compilation completed successfully!")
            self.progress_bar.setValue(100)
            self.update_button_text("compile", True)
            QMessageBox.information(self, "Success", "Compilation completed successfully!")
        else:
            self.log_message("Compilation failed!", error=True)
            self.progress_bar.setValue(0)
            self.update_button_text("compile", False)
            QMessageBox.critical(self, "Error", "Compilation failed! Check the log for details.")

    def remove_plugins(self):
        """Remove ROSUE plugins from project"""
        if not self.selected_project:
            return
            
        reply = QMessageBox.question(self, 'Remove Plugins',
            "This will remove all ROSUE plugins from your project.\n"
            "This includes both the plugin files and their entries in the project configuration.\n\n"
            "Do you want to continue?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            
        if reply != QMessageBox.Yes:
            return
            
        try:
            self.log_message("Starting plugin removal...")
            project_path = os.path.dirname(self.selected_project)
            plugins_dir = os.path.join(project_path, "Plugins")
            
            # Remove plugin directories
            plugins_to_remove = ["MetaLidar", "roscontrol", "MathToolkit"]
            for name in plugins_to_remove:
                plugin_path = os.path.join(plugins_dir, name)
                if os.path.exists(plugin_path):
                    import shutil
                    self.log_message(f"Removing plugin directory: {name}")
                    shutil.rmtree(plugin_path)
            
            # Remove from uproject file
            with open(self.selected_project, 'r') as f:
                project_data = json.load(f)
            
            if "Plugins" in project_data:
                original_count = len(project_data["Plugins"])
                project_data["Plugins"] = [p for p in project_data["Plugins"] 
                                         if p["Name"] not in plugins_to_remove]
                removed_count = original_count - len(project_data["Plugins"])
                self.log_message(f"Removed {removed_count} plugin entries from project configuration")
                
                with open(self.selected_project, 'w') as f:
                    json.dump(project_data, f, indent=4)
            
            self.log_message("Plugin removal completed successfully!")
            
            # Reset completion status
            for step in self.steps_completed:
                self.update_button_text(step, False)
            
            QMessageBox.information(self, "Success", "Plugins removed successfully!")
            
        except Exception as e:
            self.log_message(f"Error removing plugins: {str(e)}", error=True)
            QMessageBox.critical(self, "Error", f"Failed to remove plugins: {str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ROSUESetupGUI()
    window.show()
    sys.exit(app.exec_())