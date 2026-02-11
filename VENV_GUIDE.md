# Virtual Environment Usage Guide

## ✅ Virtual Environment Created!

During setup, a Python virtual environment was created in the `venv/` folder. This isolates all your earthquake ShakeMap system dependencies.

## 🚀 Using the System

### Every Time You Use the System

**Always activate the virtual environment first:**

```bash
cd /home/giorgi-chakhnashvili/Desktop/shakemap
source venv/bin/activate
```

You'll see `(venv)` appear at the start of your terminal prompt:
```
(venv) giorgi-chakhnashvili@INTERN:~/Desktop/shakemap$
```

### Then Run Your Commands

```bash
# View test maps (already generated during setup)
firefox outputs/test_maps/example_001_interactive.html

# Process your downloaded earthquakes
python main.py -m downloads

# Process a specific directory
python main.py -m batch -d /path/to/earthquake/files

# Run examples
python examples.py 1   # Single event
python examples.py 3   # Statistical analysis
```

## 📋 Recommended Setup

Create a convenient alias in your `.bashrc` file to make this easier:

```bash
# Add this line to ~/.bashrc
alias shakemap='cd /home/giorgi-chakhnashvili/Desktop/shakemap && source venv/bin/activate'
```

Then reload your shell:
```bash
source ~/.bashrc
```

Now you can simply type:
```bash
shakemap
# Automatically navigates to folder AND activates virtual environment
```

## 📦 Understanding Virtual Environments

A **virtual environment** is like a isolated Python installation just for your project. It:
- ✅ Keeps your system Python clean
- ✅ Prevents package conflicts with other projects
- ✅ Makes it easy to manage dependencies
- ✅ Is recommended by Python 3.12+

## 🔧 If You Need to Install Additional Packages

If you want to add more Python packages:

1. Activate the environment:
   ```bash
   source venv/bin/activate
   ```

2. Install the package:
   ```bash
   pip install package_name
   ```

3. Update requirements.txt (optional but recommended):
   ```bash
   pip freeze > requirements.txt
   ```

## 🚪 Exiting the Virtual Environment

Simply type:
```bash
deactivate
```

The `(venv)` prefix disappears from your prompt.

## ⚙️ Common Issues

### Issue: `python: command not found`
**Solution:** Make sure the virtual environment is activated. You should see `(venv)` in your prompt.

### Issue: `ModuleNotFoundError` when running scripts
**Solution:** Activate the virtual environment first:
```bash
source venv/bin/activate
```

### Issue: Need to reinstall package
**Solution:**
```bash
source venv/bin/activate
pip install --force-reinstall package_name
```

## 📚 More Information

- https://docs.python.org/3/tutorial/venv.html
- https://realpython.com/python-virtual-environments-a-primer/

---

**Your ShakeMap system is ready! Just remember to activate the venv each session.** 🌍⚡
