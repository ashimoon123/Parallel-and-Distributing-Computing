import csv

def generate():
    data = [
        {"Resolution": "854x480", "Local Time (s)": 45.2, "Upload Time (s)": 5.1, "Remote Render Time (s)": 10.2, "Download Time (s)": 3.8, "Total Remote Time (s)": 19.1, "Speedup (x)": 2.37},
        {"Resolution": "1280x720", "Local Time (s)": 112.5, "Upload Time (s)": 12.4, "Remote Render Time (s)": 24.5, "Download Time (s)": 9.2, "Total Remote Time (s)": 46.1, "Speedup (x)": 2.44},
        {"Resolution": "1920x1080", "Local Time (s)": 245.8, "Upload Time (s)": 28.5, "Remote Render Time (s)": 52.1, "Download Time (s)": 20.3, "Total Remote Time (s)": 100.9, "Speedup (x)": 2.44},
        {"Resolution": "3840x2160", "Local Time (s)": 890.3, "Upload Time (s)": 102.3, "Remote Render Time (s)": 185.6, "Download Time (s)": 75.1, "Total Remote Time (s)": 363.0, "Speedup (x)": 2.45}
    ]
    with open("results.csv", "w", newline='') as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
    print("results.csv populated with dummy data for graphing.")

if __name__ == "__main__":
    generate()
