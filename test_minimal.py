#!/usr/bin/env python3
"""
Minimal test to isolate the segfault issue
"""

import sys
import os
from pathlib import Path

def main():
    print("🧪 Testing minimal launcher...")
    
    try:
        # Step 1: Import basic Anki/Qt modules
        print("✅ Importing Anki modules...")
        import aqt
        from aqt.qt import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton
        import anki
        import json
        
        # Step 2: Create QApplication
        print("✅ Creating Qt application...")
        app = QApplication.instance() or QApplication([])
        
        # Step 3: Create a simple test widget instead of the full interface
        print("✅ Creating test widget...")
        
        class TestWidget(QWidget):
            def __init__(self):
                super().__init__()
                self.setWindowTitle("Test Dictionary Interface")
                layout = QVBoxLayout()
                layout.addWidget(QLabel("Dictionary Test"))
                button = QPushButton("Close")
                button.clicked.connect(self.close)
                layout.addWidget(button)
                self.setLayout(layout)
                self.resize(400, 300)
        
        test_widget = TestWidget()
        test_widget.show()
        
        print("✅ Test widget shown successfully!")
        print("✅ Basic Qt functionality works. Close window to exit.")
        
        # Run application
        app.exec()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
