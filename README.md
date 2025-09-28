# 🐒 Wukong Stack

**WukongStack** is an intelligent CLI developer tool designed to empower developers with AI-assisted code generation, project scaffolding, and advanced code review and refactor capabilities. Inspired by the legendary Monkey King, Sun Wukong, from Chinese mythology, WukongStack streamlines development by delivering a secure, testable, and modern project structure for rapid prototyping and production-ready applications.

> 🔥 _"I've got all the magic you need for your coding journey!"_

## 🚀 Features

### 💡 Project Generation
- Initialize new projects with customizable templates  
- Create full-stack web applications in seconds  

### 🤖 AI Code Assistant
- Prompt-based code generation using state-of-the-art LLMs  
- Extract and save generated code blocks directly to files  
- Stream responses for real-time coding assistance  

### 🔍 Intelligent Code Review & Refactoring
- Analyze existing codebases for logic flaws and vulnerabilities  
- Automatically refactor problematic code sections  
- Generate unit tests based on current codebase structure  

### 🧠 Interactive Shell Environment
- Persistent conversation history with Wukong AI  
- Multi-line editing support (`edit` command)  
- History management: clear, save, or show previous exchanges  

## 📦 Installation

Install via pip:
```bash
pip install wukong-stack
```

> **Note**: Requires Python 3.10+

## 💻 Usage Examples

### Initialize a new project
```bash
wukong init
```

### Create a full-stack web app skeleton
```bash
wukong create
```

### Review existing code for vulnerabilities or logic errors  
```bash
wukong review --path ./src/app.py
```

### Generate unit tests automatically from current codebase
```bash
wukong unittest --path ./src/
```

### Refactor problematic sections in your code
```bash
wukong refactor --path ./src/old_module.py
```

### Start the interactive shell for continuous assistance
```bash
wukong shell
```

### Use AI Code Assistant with custom prompts or files  
```bash
wukong code --prompt "Write a Python function that sorts a list of dictionaries by their 'name' key"
```

Or use a file:
```bash
wukong code --prompt-file ./prompts/api_setup.txt
```

Save LLM output and extract code blocks:
```bash
wukong code --prompt "Generate REST API routes for user authentication" --save-llm-output --extract-code
```

# AI Assistant Configuration Guide

Welcome to the AI Assistant setup instructions. You have two options to configure your AI assistant:

## Option 1: Use Remote OpenAI Compatible LLM (Recommended for beginners)

If you want to use a remote service like OpenAI, Anthropic, or other providers:

### Step 1: Configure Basic Settings
```bash
# Set the API key (replace YOUR_API_KEY with your actual key)
wukong config set llm.api_key YOUR_API_KEY --global

# Set the timeout in seconds (optional)
wukong config set llm.timeout 30 --global

# If using a custom base URL, set it here
# wukong config set llm.base_url https://api.openai.com/v1 --global
```

### Step 2: Verify Configuration
```bash
# Check current configuration
wukong config get llm.api_key
wukong config get llm.timeout
wukong config get llm.base_url
```

### Step 3: Test Your Setup
Run a simple test to ensure everything works:
```bash
wukong chat "Hello, how are you?"
```

---

## Option 2: Install Local LLM (For Users with GPU)

### Installing Ollama

1. Visit the official Ollama website: [https://ollama.com/download](https://ollama.com/download)
2. Download and install Ollama for your operating system
3. Follow the installation instructions specific to your OS:
   - **Windows**: Run the installer and follow prompts
   - **macOS**: Use Homebrew or download from website: `brew install ollama`
   - **Linux**: Install via package manager or curl script

4. Once installed, run Ollama server:
```bash
ollama serve
```

5. Pull a model (example with llama3):
```bash
ollama pull llama3
```

6. Configure your AI assistant to use local LLM:
```bash
wukong config set llm.base_url http://localhost:11434/v1 --global
wukong config set llm.api_key placeholder --global  # Not required for Ollama
wukong config set llm.timeout 60 --global
```

---

### Installing LM Studio

1. Visit the official LM Studio website: [https://lmstudio.ai](https://lmstudio.ai)
2. Download and install LM Studio for your operating system:
   - **Windows**: Download .exe installer
   - **macOS**: Download .dmg file
   - **Linux**: Use package manager or download from website

3. Launch LM Studio and follow the setup wizard to:
   - Install models (download preferred models like Llama, Mistral, etc.)
   - Configure local server settings
   - Set up API access if needed

4. Once installed, configure your AI assistant:
```bash
wukong config set llm.base_url http://localhost:1234/v1 --global
wukong config set llm.api_key placeholder --global  # Not required for LM Studio
wukong config set llm.timeout 60 --global
```

---

## Configuration Parameters Explained

- **llm.base_url**: The endpoint URL of your LLM service (optional for OpenAI, mandatory for local)
- **llm.api_key**: Your API authentication key
- **llm.timeout**: Maximum time in seconds to wait for responses from the AI

## Quick Setup Commands Summary

### For Remote Services:
```bash
wukong config set llm.api_key YOUR_API_KEY --global
wukong config set llm.timeout 30 --global
```

### For Local Ollama:
```bash
wukong config set llm.base_url http://localhost:11434/v1 --global
wukong config set llm.timeout 60 --global
```

### For Local LM Studio:
```bash
wukong config set llm.base_url http://localhost:1234/v1 --global
wukong config set llm.timeout 60 --global
```

---

## Troubleshooting Tips

1. **Connection Issues**: Ensure your local server is running before configuring
2. **Authentication Problems**: Double-check that your API keys are correct
3. **Timeout Errors**: Increase timeout values if you're experiencing slow responses

Choose the option that best fits your setup and requirements!

## 📄 License

MIT © [Sunny Liu](mailto:sunnyliu2@gmail.com)