import os
import json
import re
from pydantic import BaseModel
from typing import Optional

class ProjectType(BaseModel):
    language: str
    framework: Optional[str] = None

class ProjectTypeAgent:
    def __init__(self, repo_path):
        self.repo_path = repo_path

    def file_exists(self, filename):
        return os.path.isfile(os.path.join(self.repo_path, filename))

    def read_file(self, filename):
        try:
            with open(os.path.join(self.repo_path, filename), 'r', encoding='utf-8') as f:
                return f.read()
        except Exception:
            return ""

    def run(self) -> ProjectType:
        language = "Unknown"
        framework = None


        # --- PHP ---
        if self.file_exists('composer.json'):
            language = "PHP"
            composer_data = self.read_file('composer.json')
            try:
                composer_json = json.loads(composer_data)
                require = composer_json.get('require', {})
                packages = list(require.keys())
                if any("laravel/framework" in pkg for pkg in packages):
                    framework = "Laravel"
                elif any("symfony" in pkg for pkg in packages):
                    framework = "Symfony"
                elif any("cakephp/cakephp" in pkg for pkg in packages):
                    framework = "CakePHP"
                elif any("drupal/core" in pkg for pkg in packages):
                    framework = "Drupal"
                elif any("magento/product-community-edition" in pkg for pkg in packages):
                    framework = "Magento"
            except json.JSONDecodeError:
                pass

        # --- Python ---
        elif self.file_exists('requirements.txt') or self.file_exists('setup.py') or self.file_exists('pyproject.toml'):
            language = "Python"
            requirements = self.read_file('requirements.txt') + self.read_file('setup.py') + self.read_file('pyproject.toml')
            if re.search(r'django', requirements, re.I):
                framework = "Django"
            elif re.search(r'flask', requirements, re.I):
                framework = "Flask"
            elif re.search(r'fastapi', requirements, re.I):
                framework = "FastAPI"
            elif re.search(r'pyramid', requirements, re.I):
                framework = "Pyramid"


        # --- Ruby ---
        elif self.file_exists('Gemfile'):
            language = "Ruby"
            gemfile = self.read_file('Gemfile')
            if re.search(r'gem\s+"rails"', gemfile, re.I):
                framework = "Ruby on Rails"
            elif re.search(r'gem\s+"sinatra"', gemfile, re.I):
                framework = "Sinatra"

        # --- Java ---
        elif self.file_exists('pom.xml') or self.file_exists('build.gradle'):
            language = "Java"
            build_files = self.read_file('pom.xml') + self.read_file('build.gradle')
            if re.search(r'spring-boot-starter', build_files, re.I):
                framework = "Spring Boot"
            elif re.search(r'com.android', build_files, re.I):
                framework = "Android"

        # --- C# ---
        elif any(f.endswith('.csproj') for f in os.listdir(self.repo_path)):
            language = "C#"
            for file in os.listdir(self.repo_path):
                if file.endswith('.csproj'):
                    csproj_data = self.read_file(file)
                    if re.search(r'Microsoft.AspNetCore', csproj_data, re.I):
                        framework = "ASP.NET Core"

        # --- Go ---
        elif self.file_exists('go.mod'):
            language = "Go"
            go_mod = self.read_file('go.mod')
            if re.search(r'github.com/gin-gonic/gin', go_mod):
                framework = "Gin"
            elif re.search(r'github.com/labstack/echo', go_mod):
                framework = "Echo"

        # --- Rust ---
        elif self.file_exists('Cargo.toml'):
            language = "Rust"
            cargo = self.read_file('Cargo.toml')
            if re.search(r'rocket', cargo, re.I):
                framework = "Rocket"

        # --- JavaScript/TypeScript (we leave JS until last because other frameworks use it for the front-end) ---
        elif self.file_exists('package.json'):
            language = "JavaScript/TypeScript"
            package_data = self.read_file('package.json')
            try:
                package_json = json.loads(package_data)
                dependencies = package_json.get('dependencies', {})
                dev_dependencies = package_json.get('devDependencies', {})
                all_deps = {**dependencies, **dev_dependencies}
                if "react" in all_deps:
                    framework = "React"
                elif "next" in all_deps:
                    framework = "Next.js"
                elif "vue" in all_deps:
                    framework = "Vue.js"
                elif "@angular/core" in all_deps:
                    framework = "Angular"
                elif "svelte" in all_deps:
                    framework = "Svelte"
                elif "express" in all_deps:
                    framework = "Express"
            except json.JSONDecodeError:
                pass

        # --- Fallback by file extension ---
        else:
            extensions = {f.split('.')[-1] for f in os.listdir(self.repo_path) if '.' in f}
            if 'py' in extensions:
                language = "Python"
            elif 'php' in extensions:
                language = "PHP"
            elif 'js' in extensions:
                language = "JavaScript"
            elif 'rb' in extensions:
                language = "Ruby"
            elif 'java' in extensions:
                language = "Java"
            elif 'cs' in extensions:
                language = "C#"
            elif 'go' in extensions:
                language = "Go"
            elif 'rs' in extensions:
                language = "Rust"

        return ProjectType(language=language, framework=framework)
