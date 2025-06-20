import sys
import tempfile
from PyQt6.QtWidgets import (QApplication, QMainWindow, QLabel, QComboBox, 
                            QPushButton, QTextEdit, QVBoxLayout, QHBoxLayout, QWidget, 
                            QMessageBox, QSizePolicy, QGraphicsOpacityEffect)
from PyQt6.QtGui import (QFont, QIcon, QPixmap, QSyntaxHighlighter, QTextCharFormat, QColor)
from PyQt6.QtCore import Qt, QRegularExpression, QThread, pyqtSignal
import os
import logging
from main_cpp import process_file as process_cpp_to_python
from mainpython import process_file as process_python_to_cpp

# Configure logging for debugging
# logging.basicConfig(level=logging.DEBUG)

# Syntax highlighter for comments
class CommentHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None, target_language="cpp"):
        super().__init__(parent)
        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(QColor(Qt.GlobalColor.darkGreen))  # Green for comments
        self.target_language = target_language.lower()

    def set_target_language(self, language):
        self.target_language = language.lower()
        self.rehighlight()  # Reapply highlighting for new language

    def highlightBlock(self, text):
        # Highlight C++ single-line comments
        cpp_single = QRegularExpression(r"//.*$")
        match = cpp_single.match(text)
        if match.hasMatch():
            start = match.capturedStart()
            length = match.capturedLength()
            self.setFormat(start, length, self.comment_format)

        # Highlight C++ multi-line comments if target is C++
        if self.target_language == "cpp":
            self._highlight_multiline(text, r"/\*.*?\*/", self.comment_format, True)

        # Highlight Python comments, avoiding #include in C++
        if self.target_language == "python":
            python_comment = QRegularExpression(r"#.*$")
        else:
            python_comment = QRegularExpression(r"(?<!\s)#(?!(include))\s.*$")
        match = python_comment.match(text)
        if match.hasMatch():
            start = match.capturedStart()
            length = match.capturedLength()
            self.setFormat(start, length, self.comment_format)

    def _highlight_multiline(self, text, pattern, format, use_re=False):
        # Helper to highlight multi-line patterns
        if use_re:
            expr = QRegularExpression(pattern)
            match = expr.match(text)
            while match.hasMatch():
                start = match.capturedStart()
                length = match.capturedLength()
                self.setFormat(start, length, format)
                match = expr.match(text, start + length)

# Thread for running conversion without freezing UI
class ConverterThread(QThread):
    result = pyqtSignal(str)  # Signal for successful conversion
    error = pyqtSignal(str)   # Signal for errors

    def __init__(self, source_code, source_lang, target_lang):
        super().__init__()
        self.source_code = source_code
        self.source_lang = source_lang
        self.target_lang = target_lang

    def run(self):
        try:
            # Write source code to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as temp_file:
                temp_file.write(self.source_code.encode('utf-8'))
                temp_path = temp_file.name
            
            # Select conversion function based on languages
            if self.source_lang == 'c++' and self.target_lang == 'python':
                output = process_cpp_to_python(temp_path, self.source_lang, self.target_lang, verbose=True)
            elif self.source_lang == 'python' and self.target_lang == 'c++':
                output = process_python_to_cpp(temp_path, self.source_lang, self.target_lang, verbose=True)
            else:
                self.error.emit(f"Unsupported conversion from {self.source_lang} to {self.target_lang}")
                return
            
            # Process output (string or file path)
            if isinstance(output, str):
                converted_code = output
            else:
                if output is None or not os.path.exists(output):
                    self.error.emit("Conversion failed. No output file was generated or file does not exist.")
                    return
                with open(output, "r", encoding='utf-8') as file:
                    converted_code = file.read()
                if os.path.exists(output):
                    os.remove(output)  # Clean up temp output file

            if not converted_code.strip():
                self.error.emit("Converted code is empty or contains only whitespace!")
                return
            
            self.result.emit(converted_code)
        except Exception as e:
            logging.error(f"Conversion error: {str(e)}")
            self.error.emit(f"An unexpected error occurred: {str(e)}")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)  # Clean up temp input file

# Main application window
class CodeConverterWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.dragging = False  # For window dragging
        self.drag_position = None
        self.title_bar = None  
        self.init_ui()  # Set up UI

    def init_ui(self):
        # Basic window setup
        self.setWindowTitle("KENGEN: BASIC PROGRAMMMING LANGUAGE CONVERTER AND SYNTAX ANALYZER")
        self.setGeometry(100, 100, 1200, 900)
        icon_path = os.path.join(os.path.dirname(__file__), "logo.png")
        self.setWindowIcon(QIcon(icon_path))
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowMinimizeButtonHint | 
                            Qt.WindowType.WindowMaximizeButtonHint | Qt.WindowType.WindowCloseButtonHint)

        # Apply custom styling
        self.setStyleSheet("""
            QMainWindow { background-color: #3c6e71; } 
            QLabel { color: white; font-weight:bold; }
            QComboBox { background-color: #333333; color: white; border: none; border-radius: 5px; }
            QComboBox QAbstractItemView { background-color: white; color: black; 
                                          selection-background-color: #dfe7fd; selection-color: #0ead69; outline: none; }
            QTextEdit { background-color: white; color: blue; font-weight:normal; font-size:14pt; 
                        border-radius: 25px; padding: 5px; margin: 0; }
            QPushButton { background-color: #333333; color: white; border: 1px solid white; 
                          border-radius: 10px; padding: 5px; }
            QPushButton:hover { background-color: #06d6a0; color: black; }
            QPushButton:disabled { background-color: darkred; color: white; }
            QMessageBox { background-color: #404040; color: white; border-radius: 5px; }
            QScrollBar:vertical { border: none; background:transparent; width: 8px; margin:2px; height: 5%; }
            QScrollBar::handle:vertical { background: rgba(100, 100, 100, 150); border-radius: 5px; 
                                          height: 10%; padding:5px; }
        """)

        # Custom title bar with logo and buttons
        self.title_bar = QWidget()
        title_bar_layout = QHBoxLayout(self.title_bar)
        title_bar_layout.setContentsMargins(0, 0, 0, 0)
        title_bar_layout.setSpacing(0)

        logo_label = QLabel(self.title_bar)
        logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
        try:
            logo_pixmap = QPixmap(logo_path).scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, 
                                                    Qt.TransformationMode.SmoothTransformation)
            if logo_pixmap.isNull():
                raise ValueError(f"Failed to load image: {logo_path}")
            logo_label.setPixmap(logo_pixmap)
        except Exception as e:
            logging.error(f"Error loading logo image: {str(e)}")
            logo_label.setText("L")
        logo_label.setFixedSize(24, 24)
        logo_label.setStyleSheet("border-radius:5px;")
        title_bar_layout.addWidget(logo_label)

        title_label = QLabel("KENGEN: BASIC PROGRAMMMING LANGUAGE CONVERTER AND SYNTAX ANALYZER")
        title_label.setFont(QFont("Helvetica", 12))
        title_label.setStyleSheet("color:#eaf4f4; padding: 5px; font-weight:bold;")
        title_bar_layout.addWidget(title_label)

        title_bar_layout.addStretch()

        # Minimize button
        minimize_button = QLabel(self.title_bar)
        minimize_icon_path = os.path.join(os.path.dirname(__file__), "minimize.png")
        minimize_pixmap = QPixmap(minimize_icon_path).scaled(30, 30, Qt.AspectRatioMode.KeepAspectRatio, 
                                                             Qt.TransformationMode.SmoothTransformation)
        minimize_button.setPixmap(minimize_pixmap)
        minimize_button.setFixedSize(30, 30)
        minimize_button.setCursor(Qt.CursorShape.PointingHandCursor)
        minimize_button.mousePressEvent = self.minimize_window
        minimize_button.setStyleSheet("""
            QLabel { background-color: #3c6e71; border-radius: 5px; padding-right: 2px; }
            QLabel:hover { background-color: #aeb8fe; }
        """)
        title_bar_layout.addWidget(minimize_button)

        # Maximize/Restore button
        self.maximize_button = QLabel(self.title_bar)
        self.maximize_icon_path = os.path.join(os.path.dirname(__file__), "zoom.png")
        self.maximize_pixmap = QPixmap(self.maximize_icon_path).scaled(30, 30, Qt.AspectRatioMode.KeepAspectRatio, 
                                                                       Qt.TransformationMode.SmoothTransformation)
        self.maximize_button.setPixmap(self.maximize_pixmap)
        self.maximize_button.setFixedSize(30, 30)
        self.maximize_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.maximize_button.mousePressEvent = self.maximize_window
        self.maximize_button.setStyleSheet("""
            QLabel { background-color: #3c6e71; border-radius: 5px; padding-right: 2px; }
            QLabel:hover { background-color: #aeb8fe; }
        """)
        title_bar_layout.addWidget(self.maximize_button)

        # Close button
        close_button = QLabel(self.title_bar)
        close_icon_path = os.path.join(os.path.dirname(__file__), "close.png")
        close_pixmap = QPixmap(close_icon_path).scaled(20, 20, Qt.AspectRatioMode.KeepAspectRatio, 
                                                       Qt.TransformationMode.SmoothTransformation)
        close_button.setPixmap(close_pixmap)
        close_button.setFixedSize(30, 30)
        close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        close_button.mousePressEvent = self.close_window
        close_button.setStyleSheet("""
            QLabel { background-color: #fb6f92; border-radius: 5px; padding-left:4.5px; }
            QLabel:hover { background-color: darkred; }
        """)
        title_bar_layout.addWidget(close_button)

        self.title_bar.setFixedHeight(30)
        self.title_bar.setStyleSheet("background-color: #3c6e71;")

        # Main layout setup
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.addWidget(self.title_bar)

        # Logo overlay in background
        self.logo_overlay = QLabel(self)
        logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
        try:
            logo_pixmap = QPixmap(logo_path)
            if logo_pixmap.isNull():
                raise ValueError(f"Failed to load image: {logo_path}")
            max_width, max_height = 500, 500
            scaled_pixmap = logo_pixmap.scaled(max_width, max_height, Qt.AspectRatioMode.KeepAspectRatio, 
                                               Qt.TransformationMode.SmoothTransformation)
            self.logo_overlay.setPixmap(scaled_pixmap)
            self.logo_overlay.setFixedSize(scaled_pixmap.size())
            self.logo_overlay.setStyleSheet("background: transparent;")
            self.logo_overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            opacity_effect = QGraphicsOpacityEffect(self.logo_overlay)
            opacity_effect.setOpacity(0.1)
            self.logo_overlay.setGraphicsEffect(opacity_effect)
            self.position_logo_in_center()
            self.logo_overlay.raise_()
        except Exception as e:
            logging.error(f"Error loading logo overlay: {str(e)}")
            self.logo_overlay.setText("Logo Error")
            self.logo_overlay.setFixedSize(100, 100)
            self.position_logo_in_center()

        label_font = QFont("Helvetica", 16)
        text_font = QFont("Courier", 16)

        # Language selection
        source_lang_label = QLabel("Source Language:")
        source_lang_label.setFont(label_font)
        main_layout.addWidget(source_lang_label)
        self.source_lang_combo = QComboBox()
        self.source_lang_combo.addItems(["C++", "Python"])
        self.source_lang_combo.setFont(text_font)
        main_layout.addWidget(self.source_lang_combo)

        target_lang_label = QLabel("Target Language:")
        target_lang_label.setFont(label_font)
        main_layout.addWidget(target_lang_label)
        self.target_lang_combo = QComboBox()
        self.target_lang_combo.addItems(["Python", "C++"])
        self.target_lang_combo.setFont(text_font)
        main_layout.addWidget(self.target_lang_combo)

        # Auto-update target language based on source
        def update_target_language(index):
            source_lang = self.source_lang_combo.currentText()
            if source_lang == "Python":
                self.target_lang_combo.setCurrentText("C++")
            elif source_lang == "C++":
                self.target_lang_combo.setCurrentText("Python")
        
        self.source_lang_combo.currentIndexChanged.connect(update_target_language)
        update_target_language(self.source_lang_combo.currentIndex())

        self.source_lang_combo.currentIndexChanged.connect(self.clear_text_edits)
        self.target_lang_combo.currentIndexChanged.connect(self.clear_text_edits)

        # Code input/output layout
        code_layout = QHBoxLayout()
        code_layout.setContentsMargins(20, 10, 20, 10)

        input_layout = QVBoxLayout()
        source_code_label = QLabel("Input Code")
        source_code_label.setFont(label_font)
        source_code_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        input_layout.addWidget(source_code_label)
        self.source_code_text = QTextEdit()
        self.source_code_text.setFont(text_font)
        self.source_code_text.setAcceptRichText(False)  # Force plain text
        input_layout.addWidget(self.source_code_text)
        code_layout.addLayout(input_layout)

        spacer = QWidget()
        spacer.setFixedWidth(20)
        code_layout.addWidget(spacer)

        output_layout = QVBoxLayout()
        target_code_label = QLabel("Converted Code")
        target_code_label.setFont(label_font)
        target_code_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        output_layout.addWidget(target_code_label)

        self.target_code_container = QWidget()
        target_layout_inner = QVBoxLayout(self.target_code_container)
        target_layout_inner.setContentsMargins(0, 0, 0, 0)

        self.target_code_text = QTextEdit()
        self.target_code_text.setFont(text_font)
        self.target_code_text.setAcceptRichText(False)
        target_layout_inner.addWidget(self.target_code_text)

        # Copy icon for converted code
        copy_icon_path = os.path.join(os.path.dirname(__file__), "copy-icon.png")
        self.copy_icon = QLabel(self.target_code_container)
        pixmap = QPixmap(copy_icon_path).scaled(20, 20, Qt.AspectRatioMode.KeepAspectRatio, 
                                                Qt.TransformationMode.SmoothTransformation)
        self.copy_icon.setPixmap(pixmap)
        self.copy_icon.setFixedSize(24, 24)
        self.copy_icon.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_icon.mousePressEvent = self.copy_converted_code_event
        self.copy_icon.raise_()

        self.target_code_container.resizeEvent = self.resize_copy_icon
        output_layout.addWidget(self.target_code_container)
        code_layout.addLayout(output_layout)

        main_layout.addLayout(code_layout)

        # Buttons
        button_layout = QHBoxLayout()
        self.convert_button = QPushButton("Convert")
        self.convert_button.setFont(QFont("Helvetica", 12, QFont.Weight.Bold))
        self.convert_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.convert_button.clicked.connect(self.convert_code)
        button_layout.addWidget(self.convert_button)

        self.clear_button = QPushButton("Clear")
        self.clear_button.setFont(QFont("Helvetica", 12, QFont.Weight.Bold))
        self.clear_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.clear_button.clicked.connect(self.clear_code)
        button_layout.addWidget(self.clear_button)

        main_layout.addLayout(button_layout)

        code_layout.setStretch(0, 1)
        code_layout.setStretch(2, 1)

        self.resize_copy_icon(None)
        self.position_logo_in_center()

        self.comments_highlighter = CommentHighlighter(self.target_code_text.document())

    # Window control methods
    def minimize_window(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.showMinimized()
        event.accept()

    def maximize_window(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle_maximize()
        event.accept()

    def close_window(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.close()
        event.accept()

    # Window dragging
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.title_bar and self.title_bar.geometry().contains(event.position().toPoint()):
            self.dragging = True
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.dragging and event.buttons() == Qt.MouseButton.LeftButton and self.drag_position is not None:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            self.drag_position = None
            event.accept()

    def toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
            self.maximize_button.setPixmap(QPixmap(self.maximize_icon_path).scaled(30, 30, Qt.AspectRatioMode.KeepAspectRatio, 
                                                                                   Qt.TransformationMode.SmoothTransformation))
        else:
            self.showMaximized()
            self.maximize_button.setPixmap(QPixmap(self.maximize_icon_path).scaled(30, 30, Qt.AspectRatioMode.KeepAspectRatio, 
                                                                                   Qt.TransformationMode.SmoothTransformation))

    # Positioning helpers
    def resize_copy_icon(self, event):
        container_width = self.target_code_container.width()
        icon_width = self.copy_icon.width()
        self.copy_icon.move(container_width - icon_width - 10, 10)
        self.copy_icon.raise_()
        self.target_code_text.viewport().update()
        if event:
            event.accept()

    def position_logo_in_center(self):
        if hasattr(self, 'logo_overlay'):
            window_size = self.size()
            logo_size = self.logo_overlay.size()
            x = (window_size.width() - logo_size.width()) // 2
            y = (window_size.height() - logo_size.height()) // 2
            self.logo_overlay.move(x, y)
            self.logo_overlay.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.position_logo_in_center()

    # Core functionality
    def convert_code(self):
        source_code = self.source_code_text.toPlainText().strip()
        source_language = self.source_lang_combo.currentText().lower()
        target_language = self.target_lang_combo.currentText().lower()

        if not source_code:
            QMessageBox.critical(self, "Error", "Source code cannot be empty!")
            return

        if source_language == target_language:
            QMessageBox.warning(self, "Warning", "Source and Target languages are the same!")
            return

        self.comments_highlighter.set_target_language(target_language)
        self.convert_button.setEnabled(False)
        self.clear_button.setEnabled(False)

        self.thread = ConverterThread(source_code, source_language, target_language)
        self.thread.result.connect(self.on_conversion_finished)
        self.thread.error.connect(self.on_conversion_error)
        self.thread.finished.connect(self.on_thread_finished)
        self.thread.start()

    def on_conversion_finished(self, result):
        self.target_code_text.setText(result)
        self.comments_highlighter.rehighlight()
        self.target_code_text.viewport().update()

    def on_conversion_error(self, error):
        QMessageBox.critical(self, "Error", error)

    def on_thread_finished(self):
        self.convert_button.setEnabled(True)
        self.clear_button.setEnabled(True)

    def clear_code(self):
        self.source_code_text.clear()
        self.target_code_text.clear()

    def copy_converted_code_event(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            converted_code = self.target_code_text.toPlainText().strip()
            if converted_code:
                clipboard = QApplication.clipboard()
                clipboard.setText(converted_code)
                QMessageBox.information(self, "Success", "Converted code copied to clipboard!")
            else:
                QMessageBox.warning(self, "Warning", "No converted code available to copy!")
        event.accept()

    def clear_text_edits(self):
        self.source_code_text.clear()
        self.target_code_text.clear()

# Application entry point
def main():
    app = QApplication(sys.argv)
    window = CodeConverterWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()