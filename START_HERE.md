# ⚡ START HERE - Earthquake ShakeMap System

**Welcome!** You now have a complete earthquake visualization system.

## 🚀 Get Results in 5 Minutes

### Copy & Paste These Commands:

```bash
cd /home/giorgi-chakhnashvili/Desktop/shakemap
./setup.sh
```

**What happens:**
1. Creates a virtual environment (Python 3.12+ requirement)
2. Installs all dependencies (~2 min)
3. Generates example earthquake data
4. Creates sample ShakeMaps (30 seconds)
5. Maps are ready to view in `outputs/test_maps/`

### After Setup Completes

Activate the virtual environment each time you use the system:
```bash
cd /home/giorgi-chakhnashvili/Desktop/shakemap
source venv/bin/activate
```

Then you can run commands:
```bash
python main.py -m test
python main.py -m downloads
python examples.py 1
```

### View Your First ShakeMap

After commands complete, open these in your browser:
- **Interactive Map**: `outputs/test_maps/example_001_interactive.html` ⭐
- **Static Map**: `outputs/test_maps/example_001_shakemap.png`
- **Comparison**: `outputs/test_maps/all_events_comparison.html`

---

## 📊 What You're Looking At

Your ShakeMap shows:
- **Red Star** = Earthquake epicenter location
- **Colors** = Ground motion intensity (blue=weak, red=strong)  
- **Interactive** = Zoom, pan, view event info

---

## 🎯 What's Next?

### Process Your Data:
```bash
source venv/bin/activate            # Activate virtual env (one-time per session)
python main.py -m downloads         # Process all earthquakes in Downloads folder
```

### Or: Process Any Directory:
```bash
source venv/bin/activate
python main.py -m batch -d /path/to/earthquake/files
```

### Or: Run an Example:
```bash
source venv/bin/activate
python examples.py 3      # Statistical analysis
python examples.py 1      # Single event ShakeMap
python examples.py 5      # Custom earthquake
```

---

## 📚 Documentation

| Time | Document | Read This |
|------|----------|-----------|
| 2 min | [QUICKSTART.md](QUICKSTART.md) | If you're in a hurry |
| 20 min | [README.md](README.md) | For complete system info |
| 10 min | [SETUP_SUMMARY.md](SETUP_SUMMARY.md) | What was created |
| 5 min | [CONFIG.md](CONFIG.md) | How to customize |

---

## ❓ Common Questions

**Q: Can I process my own earthquake XML files?**  
A: Yes! Use: `python3 main.py -m batch -d /your/earthquake/folder`

**Q: Can I embed maps in a website?**  
A: Yes! The HTML files can be embedded with `<iframe>`.

**Q: How do I customize colors/resolution?**  
A: Edit `shakemap_generator.py` or read [CONFIG.md](CONFIG.md)

**Q: What's the system requirements?**  
A: Python 3.7+, ~500MB disk space, any operating system.

**Q: Can I schedule this to run daily?**  
A: Yes! Add to crontab: `0 6 * * * cd /shakemap && python3 main.py -m downloads`

---

## 🐛 If Something Goes Wrong

**Issue**: `pip: command not found`  
→ Install Python 3 from python.org

**Issue**: `No module named 'X'`  
→ Run: `pip3 install -r requirements.txt`

**Issue**: Permission denied on setup.sh  
→ Run: `chmod +x setup.sh` then `./setup.sh`

**Issue**: Maps look low quality  
→ Modify `grid_spacing` in shakemap_generator.py (see CONFIG.md)

---

## 📁 System Files

```
You have these files in /home/giorgi-chakhnashvili/Desktop/shakemap/:

Core Code:
  ├─ earthquake_data.py         Earthquake data & XML parsing
  ├─ shakemap_generator.py      ShakeMap creation
  ├─ analysis.py                Statistical analysis
  ├─ main.py                    Command-line interface
  └─ examples.py                Code examples

Documentation:
  ├─ README.md                  Complete guide (read this first!)
  ├─ QUICKSTART.md              2-minute quick start
  ├─ CONFIG.md                  Configuration guide
  ├─ SETUP_SUMMARY.md           What was created
  ├─ FILE_INVENTORY.md          Architecture details
  └─ START_HERE.md              This file

Setup & Data:
  ├─ setup.sh                   Automated installation
  ├─ requirements.txt           Python dependencies
  ├─ generate_example_data.py   Create example earthquakes
  └─ example_data/              Pre-made earthquake examples
     ├─ example_events/         4 example earthquakes
     └─ synthetic_catalog/      Generated earthquake catalog
```

---

## 🎓 Learning Paths

### 5 Minute Expert
1. Run `./setup.sh`
2. Run `python3 main.py -m test`
3. Open HTML file in browser
4. ✅ Done!

### 30 Minute Expert
1. Complete 5-Minute path above
2. Read QUICKSTART.md (2 min)
3. Try: `python3 examples.py 1` (30 sec)
4. Read README.md first section (10 min)
5. Process your own data: `python3 main.py -m downloads`

### Full Expert (2 hours)
1. Complete 30-Minute path above
2. Read entire README.md (20 min)
3. Study all example scripts: `python3 examples.py 1-7`
4. Read CONFIG.md (15 min)
5. Customize system for your needs

---

## 💪 You Can Now Do:

✅ Create earthquake ShakeMaps  
✅ Process earthquake catalogs  
✅ Generate statistical reports  
✅ Compare multiple earthquakes  
✅ Create interactive maps  
✅ Analyze seismic data  
✅ Share results with colleagues  
✅ Integrate into web applications  

---

## 🚀 Quick Command Reference

```bash
cd /home/giorgi-chakhnashvili/Desktop/shakemap

# First time setup
./setup.sh

# Activate virtual environment (do this each session)
source venv/bin/activate

# Generate test maps
python main.py -m test

# Process your data
python main.py -m downloads
python main.py -m batch -d /path/to/data

# Run examples
python examples.py 1   # Single event
python examples.py 2   # Batch process
python examples.py 3   # Statistics
python examples.py 4   # Synthetic catalog
python examples.py 5   # Custom event
python examples.py 6   # Advanced ShakeMap
python examples.py 7   # Compare events

# View results
firefox outputs/test_maps/example_001_interactive.html

# Exit virtual environment when done
deactivate
```

---

## 📞 Support Resources

1. **For Getting Started**: Read QUICKSTART.md (⭐ Start here!)
2. **For Virtual Environment Help**: Read VENV_GUIDE.md
3. **For Full Details**: Read README.md
4. **For Configuration**: Read CONFIG.md
5. **For Code Examples**: Review examples.py
6. **For Troubleshooting**: See README.md Troubleshooting section

---

## ✨ You're All Set!

```
$ ./setup.sh              ← Run this once to setup
$ source venv/bin/activate     ← Activate virtual env (each session)
$ python main.py -m test ← Generate test maps
$ firefox outputs/test_maps/example_001_interactive.html ← View in browser
                          → Your first ShakeMap! 🗺️⚡
```

**Estimated time to first result: 3-5 minutes**

---

**Welcome to the Earthquake ShakeMap System!**

Questions? Check [README.md](README.md) or review [examples.py](examples.py)

🌍 Made for the Georgian Seismology Institute
