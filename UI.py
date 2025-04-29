import sys
import sqlite3
from PyQt6.QtWidgets import QApplication, QProgressBar, QWidget, QVBoxLayout, QLineEdit, QPushButton, QLabel, QFileDialog, QTableWidget, QTableWidgetItem, QTabWidget, QHBoxLayout, QStackedWidget, QSpinBox
from PyQt6.QtCore import Qt, QMargins
from datetime import datetime
#import random
#from PyQt6 import QtCharts
from PyQt6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis
from PyQt6.QtGui import QPainter, QImage, QPixmap
import os
from PyQt6.QtWidgets import QSplitter
from PyQt6.QtWidgets import QHeaderView
from PyQt6.QtWidgets import QInputDialog
import mediapipe as mp
import cv2
from PyQt6.QtCore import QTimer
from Jump_Analyzer import *

class JumpHeightApp(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Vertical Jump Height Tester")
        self.setGeometry(100, 100, 600, 500)

        # Create main layout
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

        self.current_video_path = None
        self.current_user = None
        self.jump_analyzer = None 
        self.current_frame = None

        # Initialize Database
        self.initialize_database()

        # Create the stacked widget to handle screen transitions
        self.stacked_widget = QStackedWidget()
        self.main_layout.addWidget(self.stacked_widget)

        # Welcome screen (Sign-In / Sign-Up)
        self.welcome_screen = QWidget()
        self.setup_welcome_screen()
        self.stacked_widget.addWidget(self.welcome_screen)

        # Home screen (after sign-in)
        self.home_screen = QWidget()
        self.setup_home_screen()
        self.stacked_widget.addWidget(self.home_screen)

    def initialize_database(self):
        """Create or update database with proper schema."""
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        
        # Create tables if they don't exist
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        email TEXT PRIMARY KEY, 
                        password TEXT)''')
        
        # Check if height column exists, add if not
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'height' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN height INTEGER DEFAULT 72")  # Default to 72 inches
        
        # Create jump records table (unchanged)
        cursor.execute('''CREATE TABLE IF NOT EXISTS jump_records (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        email TEXT NOT NULL,
                        date TEXT NOT NULL,
                        jump_height REAL NOT NULL,
                        FOREIGN KEY(email) REFERENCES users(email))''')
        
        # Create index for faster queries
        cursor.execute('''CREATE INDEX IF NOT EXISTS idx_email 
                        ON jump_records(email)''')
        
        conn.commit()
        conn.close()

    def setup_welcome_screen(self):
        """Set up the welcome screen with sign-in and sign-up."""
        layout = QVBoxLayout()

        self.email_input = QLineEdit(self)
        self.email_input.setPlaceholderText("Email")
        self.password_input = QLineEdit(self)
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        
        self.sign_in_button = QPushButton("Sign In", self)
        self.sign_in_button.clicked.connect(self.sign_in)
        
        self.sign_up_button = QPushButton("Sign Up", self)
        self.sign_up_button.clicked.connect(self.sign_up)
        
        layout.addWidget(self.email_input)
        layout.addWidget(self.password_input)
        layout.addWidget(self.sign_in_button)
        layout.addWidget(self.sign_up_button)

        self.welcome_screen.setLayout(layout)

    def setup_home_screen(self):
        """Set up the home screen after user has signed in."""
        # Create Tab Widget
        self.tabs = QTabWidget()
        
        # Add logout button to tab corner
        self.logout_button = QPushButton("Logout")
        self.logout_button.clicked.connect(self.logout)
        self.tabs.setCornerWidget(self.logout_button, Qt.Corner.TopRightCorner)

        # Tab 1: Upload Video
        self.upload_video_tab = QWidget()
        self.setup_upload_video_tab()
        self.tabs.addTab(self.upload_video_tab, "Upload Video")

        # Tab 2: Calculate Needed Vertical
        self.calculate_vertical_tab = QWidget()
        self.setup_calculate_vertical_tab()
        self.tabs.addTab(self.calculate_vertical_tab, "Calculate Vertical")

        # Tab 3: View Vertical Data
        self.view_data_tab = QWidget()
        self.setup_view_data_tab()
        self.tabs.addTab(self.view_data_tab, "View Data")

        # Add tabs to layout
        layout = QVBoxLayout()
        layout.addWidget(self.tabs)
        self.home_screen.setLayout(layout)

    def setup_upload_video_tab(self):
        """Set up the upload video tab."""
        layout = QVBoxLayout()

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)  # Add this line
        self.progress_bar.setValue(0)       # Add this line
        
        # Video preview with aspect ratio preservation
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setStyleSheet("background-color: black;")
        layout.addWidget(self.video_label)
        
        # Processing controls
        control_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.play_pause_button = QPushButton("Pause")
        self.play_pause_button.clicked.connect(self.toggle_playback)
        
        control_layout.addWidget(self.progress_bar)
        control_layout.addWidget(self.play_pause_button)
        layout.addLayout(control_layout)

        self.upload_button = QPushButton("Upload Video", self)
        self.upload_button.clicked.connect(self.upload_video)
        layout.addWidget(self.upload_button)

        self.upload_label = QLabel("Press the button to upload a video", self)
        layout.addWidget(self.upload_label)

        self.result_label = QLabel("", self)
        layout.addWidget(self.result_label)

        self.upload_video_tab.setLayout(layout)

    def setup_calculate_vertical_tab(self):
        """Set up the vertical calculation tab with stored height."""
        layout = QVBoxLayout()

        # Display stored height
        self.height_label = QLabel("Your stored height:", self)
        layout.addWidget(self.height_label)

        self.height_display = QLabel("Loading...", self)
        layout.addWidget(self.height_display)

        # Height update button
        self.update_height_button = QPushButton("Update Height", self)
        self.update_height_button.clicked.connect(self.update_user_height)
        layout.addWidget(self.update_height_button)

        # Height input for calculation
        self.calc_height_label = QLabel("Enter height for calculation (inches):", self)
        layout.addWidget(self.calc_height_label)

        self.height_input = QSpinBox(self)
        self.height_input.setRange(48, 96)
        self.height_input.setSuffix(" inches")
        layout.addWidget(self.height_input)

        # Fixed dunk height
        self.dunk_height = 125

        # Calculate button
        self.calculate_button = QPushButton("Calculate Vertical Jump", self)
        self.calculate_button.clicked.connect(self.calculate_vertical)
        layout.addWidget(self.calculate_button)

        # Result display
        self.vertical_result_label = QLabel("", self)
        layout.addWidget(self.vertical_result_label)

        self.calculate_vertical_tab.setLayout(layout)


    def setup_view_data_tab(self):
        """Set up the tab with larger table and smaller graph."""
        layout = QVBoxLayout()

        # Statistics labels at top
        stats_layout = QHBoxLayout()
        self.best_jump_label = QLabel("Best Jump: --")
        self.average_jump_label = QLabel("Average Jump: --")
        stats_layout.addWidget(self.best_jump_label)
        stats_layout.addStretch()
        stats_layout.addWidget(self.average_jump_label)
        layout.addLayout(stats_layout)

        # Create a splitter for resizable table and chart
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Data Table (takes more space)
        self.data_table = QTableWidget()
        self.data_table.setColumnCount(3)  # Added column for delete button
        self.data_table.setHorizontalHeaderLabels(["Date", "Height (inches)", "Delete"])
        self.data_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Date
        self.data_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Height
        self.data_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Delete
        # Add these to your table setup for better readability:
        self.data_table.setStyleSheet("""
            QTableWidget {
                font-size: 12px;
            }
            QHeaderView::section {
                padding: 5px;
            }
        """)
        self.data_table.verticalHeader().setDefaultSectionSize(25)  # Row height
        splitter.addWidget(self.data_table)

        # Chart (smaller section)
        self.chart_view = QChartView()
        self.chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        splitter.addWidget(self.chart_view)

        # Set initial sizes (table gets 70%, chart gets 30%)
        splitter.setSizes([500, 500])
        
        layout.addWidget(splitter)
        self.view_data_tab.setLayout(layout)

    def create_jump_history_chart(self, jump_data):
        series = QLineSeries()
        
        # Handle both (id, date, height) and (date, height) formats
        for attempt, record in enumerate(jump_data):
            if len(record) == 3:  # If (id, date, height)
                date, height = record[1], record[2]
            else:  # If (date, height)
                date, height = record[0], record[1]
                
            series.append(attempt, float(height))
        
        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("")
        chart.legend().hide()
        chart.setMargins(QMargins(0, 0, 0, 0))  # Minimize margins
        
        # Customize axes to be compact
        axis_x = QValueAxis()
        axis_x.setTitleText("Attempt")
        axis_x.setLabelsVisible(False)  # Hide x-axis labels to save space
        
        axis_y = QValueAxis()
        axis_y.setTitleText("Inches")
        axis_y.setLabelFormat("%.0f")
        
        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_x)
        series.attachAxis(axis_y)
        # In create_jump_history_chart():
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)  # Add animation
        #series.setPointsVisible(True)  # Show data points
        #series.setPointLabelsVisible(True)  # Show values on points
        #series.setPointLabelsFormat("@yPoint inches")  # Format labels
        
        self.chart_view.setChart(chart)

    def update_jump_statistics(self, jump_data):
        """Update the best and average jump height labels."""
        # Extract jump heights from the jump data
        heights = [data[1] for data in jump_data]

        # If there are heights, calculate best and average jumps
        if heights:
            best_jump = max(heights)  # Find the highest jump
            average_jump = sum(heights) / len(heights)  # Calculate average jump height
        else:
            best_jump = 0
            average_jump = 0

        # Update the labels to reflect best and average jumps
        self.best_jump_label.setText(f"Best Jump: {best_jump} inches")
        self.average_jump_label.setText(f"Average Jump: {average_jump:.2f} inches")

    def save_jump_data(self, jump_height):
        """Save jump record to database."""
        if not hasattr(self, "current_user"):
            return

        try:
            conn = sqlite3.connect("users.db")
            conn.execute("PRAGMA foreign_keys = ON")
            cursor = conn.cursor()
            
            current_date = datetime.now().strftime("%m/%d/%Y %I:%M:%S %p")
            cursor.execute('''INSERT INTO jump_records 
                            (email, date, jump_height)
                            VALUES (?, ?, ?)''',
                        (self.current_user, current_date, jump_height))
            
            conn.commit()
            self.load_user_data()  # Refresh display
            
        except sqlite3.Error as e:
            print(f"Database error: {e}")
        finally:
            conn.close()


    def sign_in(self):
        """Authenticate user and load their data including height."""
        email = self.email_input.text().strip()
        password = self.password_input.text().strip()

        try:
            conn = sqlite3.connect("users.db")
            cursor = conn.cursor()
            cursor.execute('''SELECT height FROM users 
                            WHERE email=? AND password=?''',
                        (email, password))
            result = cursor.fetchone()
            
            if result:
                self.current_user = email
                self.load_user_data()
                self.load_user_height()
                self.stacked_widget.setCurrentWidget(self.home_screen)
            else:
                self.show_message("Error", "Invalid email or password")
        except sqlite3.Error as e:
            self.show_message("Database Error", str(e))
        finally:
            conn.close()

    def logout(self):
        """Clean up resources"""
        if hasattr(self, 'cap') and self.cap.isOpened():
            self.cap.release()
        if hasattr(self, 'timer'):
            self.timer.stop()
        """Clear user session and return to welcome screen."""
        self.current_user = None
        self.email_input.clear()
        self.password_input.clear()
        self.stacked_widget.setCurrentWidget(self.welcome_screen)
        
        # Clear any displayed data
        self.data_table.setRowCount(0)
        self.best_jump_label.setText("Best Jump: --")
        self.average_jump_label.setText("Average Jump: --")

    def sign_up(self):
        """Register a new user with height information."""
        email = self.email_input.text().strip()
        password = self.password_input.text().strip()
        
        # Get height from user
        height, ok = QInputDialog.getInt(
            self, 
            "Height Information",
            "Enter your height in inches (48-96):",
            min=48, max=96, value=72
        )
        
        if not ok:
            return  # User cancelled

        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT 1 FROM users WHERE email=?", (email,))
            if cursor.fetchone():
                self.show_message("Error", "Email already registered.")
            else:
                cursor.execute(
                    "INSERT INTO users (email, password, height) VALUES (?, ?, ?)",
                    (email, password, height)
                )
                conn.commit()
                self.show_message("Success", "Account created! You can now sign in.")
        except sqlite3.Error as e:
            self.show_message("Database Error", str(e))
        finally:
            conn.close()

    def upload_video(self):
        """Handle video upload and store path."""
        file, _ = QFileDialog.getOpenFileName(
            self,
            "Open Video File",
            "",
            "Video Files (*.mp4 *.avi *.mov);;All Files (*)"
        )
        
        if file:
            self.current_video_path = file
            self.upload_label.setText(f"Video loaded: {os.path.basename(file)}")
            self.calculate_jump_height()  # Process the video
        

    def calculate_jump_height(self):
        self.progress_bar.setValue(0)
        if not hasattr(self, 'current_video_path'):
            self.result_label.setText("Error: No video provided")
            return

        # Get user's height from database
        try:
            conn = sqlite3.connect("users.db")
            cursor = conn.cursor()
            cursor.execute("SELECT height FROM users WHERE email=?", (self.current_user,))
            user_height_inches = cursor.fetchone()[0]
            user_height_meters = user_height_inches * 0.0254  # Convert to meters
            conn.close()
            
            # Initialize analyzer
            self.jump_analyzer = JumpAnalyzer(user_height_meters)
            
            # Setup video capture
            self.cap = cv2.VideoCapture(self.current_video_path)
            self.timer = QTimer()
            self.timer.timeout.connect(self.process_next_frame)
            self.timer.start(30)  # ~30fps
            
            self.result_label.setText("Processing video...")
            self.com_positions = []
            
        except Exception as e:
            self.result_label.setText(f"Error: {str(e)}")


    def load_user_data(self):
        """Load data with delete buttons for each row."""
        if not hasattr(self, "current_user"):
            return

        try:
            conn = sqlite3.connect("users.db")
            cursor = conn.cursor()
            # Get data in chronological order for the chart
            cursor.execute('''SELECT date, jump_height FROM jump_records 
                            WHERE email=? ORDER BY date ASC''',  # Changed to ASC
                        (self.current_user,))
            chart_data = cursor.fetchall()
            
            # Get data in reverse order for the table (most recent first)
            cursor.execute('''SELECT id, date, jump_height FROM jump_records 
                            WHERE email=? ORDER BY date DESC''',
                        (self.current_user,))
            table_data = cursor.fetchall()
            
            self.data_table.setRowCount(len(table_data))
            for row, (record_id, date, height) in enumerate(table_data):
                # Date column
                date_item = QTableWidgetItem(date)
                date_item.setFlags(date_item.flags() ^ Qt.ItemFlag.ItemIsEditable)
                self.data_table.setItem(row, 0, date_item)
                
                # Height column (ensure it's stored as float)
                try:
                    height_float = float(height)
                    height_item = QTableWidgetItem(f"{height_float:.1f}")
                except (ValueError, TypeError):
                    height_item = QTableWidgetItem("N/A")
                    
                height_item.setFlags(height_item.flags() ^ Qt.ItemFlag.ItemIsEditable)
                self.data_table.setItem(row, 1, height_item)
                
                # Delete button
                delete_btn = QPushButton("Delete")
                delete_btn.clicked.connect(lambda _, r=row, id=record_id: self.delete_entry(r, id))
                self.data_table.setCellWidget(row, 2, delete_btn)
            
                   # Update stats and chart with chronological data
                self.update_statistics(chart_data)
                if chart_data:
                    self.create_jump_history_chart(chart_data)
                
        except sqlite3.Error as e:
            print(f"Database error: {e}")
        finally:
            conn.close()

    def delete_entry(self, row, record_id):
        """Delete an entry from the database and refresh the view."""
        try:
            conn = sqlite3.connect("users.db")
            cursor = conn.cursor()
            cursor.execute("DELETE FROM jump_records WHERE id=?", (record_id,))
            conn.commit()
            
            # Remove the row from the table
            self.data_table.removeRow(row)
            
            # Reload data to update stats and chart
            self.load_user_data()
            
        except sqlite3.Error as e:
            print(f"Error deleting record: {e}")
        finally:
            conn.close()

    def update_statistics(self, jump_data):
        """Calculate and display jump statistics with proper type handling."""
        if not jump_data:
            self.best_jump_label.setText("Best Jump: --")
            self.average_jump_label.setText("Average Jump: --")
            return
        
        try:
            # Extract and convert heights to float
            heights = []
            for record in jump_data:
                try:
                    # Handle both (id, date, height) and (date, height) formats
                    height = float(record[-1])  # Last element is always height
                    heights.append(height)
                except (ValueError, IndexError, TypeError):
                    continue  # Skip invalid entries
            
            if heights:
                best = max(heights)
                average = sum(heights)/len(heights)
                self.best_jump_label.setText(f"Best Jump: {best:.1f} inches")
                self.average_jump_label.setText(f"Average Jump: {average:.1f} inches")
            else:
                self.best_jump_label.setText("Best Jump: --")
                self.average_jump_label.setText("Average Jump: --")
                
        except Exception as e:
            print(f"Error calculating statistics: {e}")
            self.best_jump_label.setText("Best Jump: Error")
            self.average_jump_label.setText("Average Jump: Error")

    def load_user_height(self):
        """Load and display the user's stored height."""
        if not hasattr(self, "current_user"):
            return

        try:
            conn = sqlite3.connect("users.db")
            cursor = conn.cursor()
            cursor.execute("SELECT height FROM users WHERE email=?", (self.current_user,))
            result = cursor.fetchone()
            
            if result and result[0] is not None:
                height = result[0]
                self.height_display.setText(f"{height} inches")
                if hasattr(self, 'height_input'):
                    self.height_input.setValue(height)
            else:
                self.height_display.setText("Not set")
                
        except (sqlite3.Error, TypeError) as e:
            print(f"Error loading height: {e}")
            self.height_display.setText("Error loading height")
        finally:
            conn.close()

    def update_user_height(self):
        """Update the user's stored height."""
        if not hasattr(self, "current_user"):
            return

        height, ok = QInputDialog.getInt(
            self, 
            "Update Height",
            "Enter your new height in inches:",
            min=48, max=96, value=self.height_input.value() if hasattr(self, 'height_input') else 72
        )
        
        if ok:
            try:
                conn = sqlite3.connect("users.db")
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE users SET height=? WHERE email=?",
                    (height, self.current_user)
                )
                conn.commit()
                self.load_user_height()  # Refresh display
            except sqlite3.Error as e:
                print(f"Error updating height: {e}")
            finally:
                conn.close()

    def check_and_migrate_user_height(self, email):
        """Ensure existing users have height value."""
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        try:
            # Check if user exists and has no height
            cursor.execute("SELECT height FROM users WHERE email=?", (email,))
            result = cursor.fetchone()
            if result and result[0] is None:
                height, ok = QInputDialog.getInt(
                    self,
                    "Height Required",
                    "Please enter your height in inches:",
                    min=48, max=96, value=72
                )
                if ok:
                    cursor.execute(
                        "UPDATE users SET height=? WHERE email=?",
                        (height, email)
                    )
                    conn.commit()
        except sqlite3.Error as e:
            print(f"Migration error: {e}")
        finally:
            conn.close()

    def calculate_vertical(self):
        """Calculate needed vertical jump using either stored or input height."""
        try:
            # Try to use stored height first
            if hasattr(self, 'height_input'):
                height_in = self.height_input.value()
            else:
                # Fallback to database value
                conn = sqlite3.connect("users.db")
                cursor = conn.cursor()
                cursor.execute("SELECT height FROM users WHERE email=?", (self.current_user,))
                height_in = cursor.fetchone()[0]
                conn.close()
            
            estimated_reach = round(height_in + 14)
            needed_vert = self.dunk_height - estimated_reach

            self.vertical_result_label.setText(
                f"Estimated standing reach: {estimated_reach} inches\n"
                f"Vertical jump needed to dunk: {needed_vert} inches"
            )
            
        except Exception as e:
            self.vertical_result_label.setText(f"Error: {str(e)}")

    def process_next_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            self.finish_processing()
            return
        
        # Process frame
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.jump_analyzer.pose.process(frame_rgb)
        
        # Store COM position if detected
        if results.pose_landmarks:
            com_y = self.jump_analyzer.estimate_center_of_mass(
                results.pose_landmarks.landmark, 
                frame.shape[0]
            )
            if com_y is not None:
                self.com_positions.append(com_y)
            
            # Draw landmarks
            mp.solutions.drawing_utils.draw_landmarks(
                frame, results.pose_landmarks, self.jump_analyzer.mp_pose.POSE_CONNECTIONS)
        
        # Display frame
        self.display_frame(frame)

    def display_frame(self, frame):
        """Convert OpenCV frame to QImage and display it"""
        # Convert color space (BGR → RGB)
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Create QImage
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(
            rgb_image.data, 
            w, h, 
            bytes_per_line, 
            QImage.Format.Format_RGB888
        )
        
        # Scale and display
        self.video_label.setPixmap(
            QPixmap.fromImage(qt_image).scaled(
                self.video_label.width(),
                self.video_label.height(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
        )

    def toggle_playback(self):
        """Pause/resume video processing"""
        if self.timer.isActive():
            self.timer.stop()
            self.play_pause_button.setText("Resume")
        else:
            self.timer.start(30)
            self.play_pause_button.setText("Pause")

    def process_next_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            self.finish_processing()
            return
        
        # Process with MediaPipe
        results = self.process_frame_with_landmarks(frame)
        
        # Display the processed frame
        self.display_frame(frame)
        
        # Update progress
        #self.update_processing_progress()

    def update_processing_progress(self):
        """Update progress bar based on video position"""
        if hasattr(self, 'cap') and self.cap.isOpened():
            # Get current frame position and total frames
            current_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
            total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # Calculate percentage and update progress bar
            if total_frames > 0:
                progress = int((current_frame / total_frames) * 100)
                self.progress_bar.setValue(progress)

    def process_frame_with_landmarks(self, frame):
        """Process frame and draw pose landmarks"""
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.jump_analyzer.pose.process(frame_rgb)
        
        if results.pose_landmarks:
            # Draw landmarks on original BGR frame
            mp.solutions.drawing_utils.draw_landmarks(
                frame,
                results.pose_landmarks,
                self.jump_analyzer.mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec=mp.solutions.drawing_styles.get_default_pose_landmarks_style()
            )
            
            # Track center of mass
            com_y = self.jump_analyzer.estimate_center_of_mass(
                results.pose_landmarks.landmark,
                frame.shape[0]
            )
            if com_y is not None:
                self.com_positions.append(com_y)
                # Visualize COM
                cv2.circle(frame, (frame.shape[1]//2, int(com_y)), 5, (0, 255, 0), -1)
        
        return results
    
    def cleanup_video_resources(self):
        """Properly release video resources"""
        if hasattr(self, 'cap'):
            self.cap.release()
        if hasattr(self, 'timer'):
            self.timer.stop()
        self.current_frame = None

    def finish_processing(self):
        self.cleanup_video_resources()
        self.progress_bar.setValue(100)
        
        if hasattr(self, 'com_positions') and self.com_positions:
            jump_height_meters, _ = self.jump_analyzer.analyze_jump(self.current_video_path)
            if jump_height_meters:
                jump_height_inches = jump_height_meters / 0.0254
                self.save_jump_data(jump_height_inches)
                self.show_results(jump_height_inches)
                return
        
        self.show_error_message()

    def show_results(self, jump_height_inches):
        """Display successful results"""
        self.result_label.setText(f"Jump Height: {jump_height_inches:.1f} inches")
        if self.data_table.rowCount() > 0:
            self.data_table.selectRow(0)
        self.video_label.setText("Processing complete")

    def show_error_message(self):
        """Handle processing failures"""
        self.result_label.setText("Error: Could not calculate jump height")
        self.video_label.setText("Processing failed - try again")

    def show_message(self, title, message):
        """Show a message box with the given title and message."""
        from PyQt6.QtWidgets import QMessageBox
        msg = QMessageBox()
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.exec()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = JumpHeightApp()
    window.show()
    sys.exit(app.exec())
