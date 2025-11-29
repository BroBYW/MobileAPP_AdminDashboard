# MentalTrack Admin Dashboard

A responsive admin dashboard for the MentalTrack app, built with [NiceGUI](https://nicegui.io/) and Python. It connects to Firebase Realtime Database to manage users, view journal entries, and analyze mood data.

## Features

- **Authentication**: Secure admin login with session management.
- **Overview**: Real-time metrics for total users, journals, and average mood.
- **Users Management**: Searchable table of users with profile details and recent journals.
- **Journals Review**: Filter journals by search term and date ranges (presets or custom).
- **Analytics**: Visual breakdown of user moods using interactive charts.
- **Export**: Download user and journal data as CSV.

## Prerequisites

- Python 3.10+
- A Firebase Realtime Database URL (public read access or authenticated).

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/mentaltrack-admin.git
   cd mentaltrack-admin
   ```

2. **Create a virtual environment** (optional but recommended):
   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # Mac/Linux
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**:
   Create a `.env` file in the root directory (do NOT commit this file). Add your admin credentials and secrets:
   ```env
   ADMIN_EMAIL=admin@mentaltrack.com
   ADMIN_PASSWORD=your_secure_password
   STORAGE_SECRET=a_long_random_string_for_cookies
   ```

## Usage

1. **Start the server**:
   ```bash
   python main.py
   ```

2. **Access the dashboard**:
   Open your browser and navigate to `http://localhost:8080`.

3. **Login**:
   Use the credentials defined in your `.env` file.

## Project Structure

- `main.py`: Core application logic and UI definitions.
- `requirements.txt`: Python dependencies.
- `.env`: Local configuration (ignored by git).

## Technologies

- **NiceGUI**: Web framework for the UI.
- **Requests**: HTTP client for Firebase API.
- **ECharts**: Data visualization.
- **Python-dotenv**: Environment variable management.
