import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from math import log
import random
import pyttsx3
import csv
import threading
import os

# Cấu hình đường dẫn file
DATA_FILE = r"d:\EDUENG\data.csv"
HISTORY_FILE = r"d:\EDUENG\history.csv"

class EnglishAppTk:
    def __init__(self, root):
        self.root = root
        self.root.title("English Master - Spaced Repetition")
        self.root.geometry("500x650")
        
        self.data = []
        self.current_word = None
        self.is_listening = False
        self.load_data()

        # Giao diện Tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill="both")

        self.setup_study_tab()
        self.setup_add_tab()
        
        # Bắt đầu học từ đầu tiên
        self.next_question()

    def load_data(self):
        self.data = []
        if not os.path.exists(DATA_FILE):
            return
        with open(DATA_FILE, mode="r", encoding='utf-8-sig') as file:
            reader = csv.reader(file)
            self.head = next(reader)
            for row in reader:
                if not row: continue
                # Parsing data: STT, voca, tran, nextTime, time, S, k, p, sd, w
                row[3] = datetime.strptime(row[3], "%d%m%Y-%H%M%S")
                row[4] = datetime.strptime(row[4], "%d%m%Y-%H%M%S")
                row[5], row[6], row[7], row[8], row[9] = map(float, [row[5], row[6], row[7], row[8], row[9]])
                row[0] = int(row[0])
                self.data.append(row)
        self.data.sort(key=lambda x: x[3])

    def save_data(self):
        self.data.sort(key=lambda x: x[3])
        with open(DATA_FILE, mode="w", encoding='utf-8-sig', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["STT", "Từ vựng", "Nghĩa", "nextTime", "time", "S", "k", "p", "sd", "w"])
            for i, row in enumerate(self.data, 1):
                row[0] = i
                save_row = list(row)
                save_row[3] = save_row[3].strftime("%d%m%Y-%H%M%S")
                save_row[4] = save_row[4].strftime("%d%m%Y-%H%M%S")
                writer.writerow(save_row)

    def setup_study_tab(self):
        self.study_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.study_tab, text="Học tập")

        self.lbl_mode = ttk.Label(self.study_tab, text="", font=("Arial", 10, "italic"))
        self.lbl_mode.pack(pady=10)

        self.lbl_question = ttk.Label(self.study_tab, text="Nghĩa của từ", font=("Arial", 18, "bold"), wraplength=400)
        self.lbl_question.pack(pady=20)

        self.btn_speak = ttk.Button(self.study_tab, text="🔊 Nghe lại", command=self.play_audio)
        self.btn_speak.pack(pady=5)
        
        self.ent_answer = ttk.Entry(self.study_tab, font=("Arial", 14), width=30)
        self.ent_answer.pack(pady=10)
        self.ent_answer.bind("<Return>", lambda e: self.check_answer())

        self.btn_check = ttk.Button(self.study_tab, text="Kiểm tra", command=self.check_answer)
        self.btn_check.pack(pady=5)

        self.lbl_result = ttk.Label(self.study_tab, text="", font=("Arial", 12))
        self.lbl_result.pack(pady=10)

        # Group nút đánh giá
        self.feedback_frame = ttk.LabelFrame(self.study_tab, text="Bạn thấy từ này thế nào?")
        self.feedback_buttons = []
        btns = [("Quên", 0), ("Khó", 1), ("Vừa", 2), ("Dễ", 3)]
        for text, val in btns:
            b = ttk.Button(self.feedback_frame, text=text, command=lambda v=val: self.process_feedback(v))
            b.pack(side="left", padx=5, pady=5)
            self.feedback_buttons.append(b)

        self.btn_next = ttk.Button(self.study_tab, text="Tiếp theo ➡️", command=self.next_question)
        # Nút này sẽ được pack sau khi hoàn thành một từ

    def setup_add_tab(self):
        self.add_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.add_tab, text="Thêm từ mới")

        ttk.Label(self.add_tab, text="Từ tiếng Anh:").pack(pady=(20, 0))
        self.ent_new_voca = ttk.Entry(self.add_tab, font=("Arial", 12), width=30)
        self.ent_new_voca.pack(pady=5)

        ttk.Label(self.add_tab, text="Nghĩa tiếng Việt:").pack(pady=(10, 0))
        self.ent_new_tran = ttk.Entry(self.add_tab, font=("Arial", 12), width=30)
        self.ent_new_tran.pack(pady=5)

        ttk.Button(self.add_tab, text="Lưu từ", command=self.add_word).pack(pady=20)

    def play_audio(self):
        if self.current_word and self.current_word[1]:
            # Phát âm trong một luồng riêng để tránh làm treo GUI 
            # và sửa lỗi engine bị "câm" sau lần gọi đầu tiên.
            threading.Thread(target=self._execute_speak, args=(self.current_word[1],), daemon=True).start()

    def _execute_speak(self, text):
        try:
            # Khởi tạo engine cục bộ trong luồng để đảm bảo tính ổn định
            speaker = pyttsx3.init()
            speaker.setProperty('rate', 140)  # Tốc độ chậm hơn một chút để nghe rõ (140)
            voices = speaker.getProperty('voices')
            
            # Ưu tiên tìm giọng nữ tiếng Anh (Zira, Samantha, hoặc có chữ 'female')
            selected_voice = None
            for v in voices:
                v_name = v.name.lower()
                if "english" in v_name and any(x in v_name for x in ["female", "zira", "samantha", "susan", "hazel"]):
                    selected_voice = v.id
                    break
            
            # Nếu tìm được giọng nữ thì thiết lập, nếu không thì lấy giọng tiếng Anh đầu tiên tìm thấy
            if selected_voice:
                speaker.setProperty('voice', selected_voice)
            else:
                for v in voices:
                    if "english" in v.name.lower():
                        speaker.setProperty('voice', v.id)
                        break

            speaker.say(text)
            speaker.runAndWait()
            speaker.stop() # Dừng hẳn engine sau khi nói xong
        except:
            pass

    def next_question(self):
        if not self.data:
            self.lbl_question.config(text="Hãy thêm từ vựng để bắt đầu!")
            return

        self.current_word = self.data[0]
        self.is_listening = random.random() < 0.4
        # self.is_listening = random.random() <= 1
        
        self.ent_answer.delete(0, tk.END)
        self.ent_answer.config(state="normal")
        self.lbl_result.config(text="")
        self.feedback_frame.pack_forget()
        self.btn_next.pack_forget()
        self.btn_check.config(state="normal")
        for b in self.feedback_buttons: b.config(state="normal")

        if self.is_listening:
            self.lbl_mode.config(text="CHẾ ĐỘ: NGHE (Dictation)", foreground="blue")
            self.lbl_question.config(text="???")
            self.play_audio()
        else:
            self.lbl_mode.config(text="CHẾ ĐỘ: DỊCH NGHĨA", foreground="green")
            self.lbl_question.config(text=self.current_word[2])
        
        self.ent_answer.focus()

    def check_answer(self):
        user_voca = self.ent_answer.get().strip()
        if not user_voca: return

        self.quality = SequenceMatcher(None, user_voca.lower(), self.current_word[1].lower()).ratio()
        color = "green" if self.quality > 0.8 else "orange" if self.quality > 0.5 else "red"
        
        self.lbl_result.config(
            text=f"Độ chính xác: {self.quality*100:.1f}%\nĐáp án đúng: {self.current_word[1]}",
            foreground=color
        )
        
        self.ent_answer.config(state="disabled")
        self.btn_check.config(state="disabled")
        self.feedback_frame.pack(pady=20)

    def process_feedback(self, feedback_idx):
        feedback_val = [0.1, 0.5, 0.75, 1][feedback_idx]
        # SRS Logic
        score = feedback_val * self.current_word[9] + self.quality * (1 - self.current_word[9])
        
        if score <= 0.1:
            self.current_word[5] = 15.0
            self.current_word[6] = 1.0
            self.current_word[7] = 0.0
            self.current_word[8] = 0
        elif score <= 0.6:
            self.current_word[5] = 15.0
            self.current_word[6] -= 0.1
        else:
            diff = datetime.now() - self.current_word[4]
            d = diff.total_seconds() / 86400  # Tính chính xác số ngày trôi qua (số thực)
            self.current_word[7] = max(0.0, self.current_word[7] + (2*self.quality - 1) * d)
            self.current_word[8] += d
            self.current_word[5] = self.current_word[5] / (self.current_word[6] * score * (self.current_word[7] + 1))
            self.current_word[6] += 0.1

        # Cập nhật thời gian
        self.current_word[4] = datetime.now().replace(microsecond=0)
        time_val = -log(0.9) / max(0.001, self.current_word[5])
        self.current_word[3] = self.current_word[4] + timedelta(days=time_val)

        self.log_history(timedelta(days=time_val), feedback_val)
        self.save_data()

        # 1. Tự động đọc từ vựng sau khi người dùng đánh giá
        self.play_audio()
        
        # 2. Khóa các nút đánh giá để tránh bấm nhầm nhiều lần
        for b in self.feedback_buttons: b.config(state="disabled")
        
        # 3. Hiện nút "Tiếp theo" để người dùng chủ động chuyển từ
        self.btn_next.pack(pady=15)
        self.load_data() # Cập nhật lại hàng đợi ngầm

    def log_history(self, delta, feedback):
        with open(HISTORY_FILE, mode="a", encoding='utf-8-sig', newline='') as file:
            writer = csv.writer(file)
            history = [
                self.current_word[4].strftime("%d%m%Y"),
                self.current_word[4].strftime("%H%M%S"),
                self.current_word[1], self.current_word[2], self.ent_answer.get(),
                str(delta), self.current_word[3].strftime("%d%m%Y-%H%M%S"),
                round(self.quality, 2), feedback, 
                round(self.current_word[5], 2), round(self.current_word[6], 2),
                round(self.current_word[7], 2), self.current_word[8], self.current_word[9]
            ]
            writer.writerow(history)

    def add_word(self):
        v = self.ent_new_voca.get().strip()
        t = self.ent_new_tran.get().strip()
        if v and t:
            now = datetime.now().replace(microsecond=0)
            # STT, voca, tran, nextTime, time, S, k, p, sd, w
            new_row = [len(self.data) + 1, v, t, now, now, 15.0, 1.0, 0.0, 0, 0.5]
            
            # Ghi trực tiếp vào file thay vì đợi save_data để đảm bảo an toàn
            file_exists = os.path.isfile(DATA_FILE)
            with open(DATA_FILE, mode="a", encoding='utf-8-sig', newline='') as file:
                writer = csv.writer(file)
                if not file_exists:
                    writer.writerow(["STT", "Từ vựng", "Nghĩa", "nextTime", "time", "S", "k", "p", "sd", "w"])
                save_row = list(new_row)
                save_row[3] = save_row[3].strftime("%d%m%Y-%H%M%S")
                save_row[4] = save_row[4].strftime("%d%m%Y-%H%M%S")
                writer.writerow(save_row)
            
            messagebox.showinfo("Thành công", f"Đã thêm từ: {v}")
            self.ent_new_voca.delete(0, tk.END)
            self.ent_new_tran.delete(0, tk.END)
            self.load_data()
            if not self.current_word: self.next_question()
        else:
            messagebox.showwarning("Chú ý", "Vui lòng nhập đầy đủ thông tin!")

if __name__ == "__main__":
    root = tk.Tk()
    app = EnglishAppTk(root)
    root.mainloop()