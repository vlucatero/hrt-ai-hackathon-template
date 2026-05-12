# 🏋️ Fitness Center Foot Traffic Tracker

A web dashboard for tracking and analyzing visitor foot traffic across Cal State East Bay's fitness centers, helping staff optimize operations and giving patrons real-time busyness insights.

## What It Does

- **Logs and analyzes daily check-ins** by date, time, and campus — with heatmaps and trend charts that reveal peak hours, slow periods, and day-of-week patterns
- **Compares both campuses** (Turlock and Stockton) side by side, showing hourly, daily, and seasonal traffic differences
- **Analyzes semester-level membership data** from Fusion Innosoft, including visit frequency, gender breakdown, engagement tiers, and member retention across Fall 2023 and Spring 2024

## How to Use

1. **Select a campus** from the sidebar (Turlock, Stockton, or Both Campuses)
2. **Daily Traffic Log tab** — Record visitor check-ins using the Quick Log button for instant one-tap logging, or enter a specific date, time, and visitor count manually; charts and trend analysis update automatically as data grows
3. **Fusion Innosoft Analytics tab** — View semester-level membership trends including total visits, gender breakdown, most active members, and how many members returned between semesters
4. **Data tab** — Browse, download, or import historical check-in records; view the full processed membership dataset

## Data

| Source | Description |
|--------|-------------|
| `data_ai/facility_usage_fall_2023.csv` | AI-generated membership data for Fall 2023 (1,888 members), modeled after Fusion Innosoft export format |
| `data_ai/facility_usage_spring_2024.csv` | AI-generated membership data for Spring 2024 (2,112 members) |
| `data_ai/fitness_traffic.csv` | Live check-in log recorded by staff through the app |

Historical check-ins can also be imported via CSV upload (columns: `date`, `time`, `visitors`, `campus`).

## Built With

- [Streamlit](https://streamlit.io) — Web app framework
- [Pandas](https://pandas.pydata.org) — Data processing and analysis
- [Plotly](https://plotly.com/python/) — Interactive charts and heatmaps
