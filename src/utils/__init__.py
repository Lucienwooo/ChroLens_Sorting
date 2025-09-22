def check_for_updates():
    import requests
    import subprocess
    import os
    import json
    from tkinter import messagebox

    # GitHub repository information
    repo_owner = "Lucienwooo"
    repo_name = "ChroLens_Sorting"
    api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest"

    try:
        response = requests.get(api_url)
        response.raise_for_status()
        latest_release = response.json()
        latest_version = latest_release["tag_name"]

        # Read current version from a file or define it here
        current_version = "1.1"  # Replace with your current version logic

        if latest_version != current_version:
            # Update the repository
            subprocess.run(["git", "pull"], check=True)
            messagebox.showinfo("更新成功", f"已更新到最新版本：{latest_version}")
        else:
            messagebox.showinfo("無需更新", "您已擁有最新版本。")

    except requests.RequestException as e:
        messagebox.showerror("錯誤", f"無法檢查更新：{e}")
    except subprocess.CalledProcessError as e:
        messagebox.showerror("錯誤", f"更新失敗：{e}")

# This file is intentionally left blank.