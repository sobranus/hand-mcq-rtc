import csv

class Data():
    def __init__(self, data):
        self.question_text = data["question_text"]
        self.question_image = data["question_image"]
        self.choice_type = data["choice_type"]
        self.answer = int(data["answer"])
        self.choice1 = data["choice1"]
        self.choice2 = data["choice2"]
        self.choice3 = data["choice3"]
        self.choice4 = data["choice4"]

        self.chosen_answer = None

def import_quiz_data(quiz_name):
    data = []
    with open(f'test_rtc/quiz/{quiz_name}.csv', newline='') as file:
        reader = csv.DictReader(file)
        datas = list(reader)
    for question in datas:
        data.append(Data(question))
    qTotal = len(data)
    q = data[1]
    print(qTotal, q)
    
import_quiz_data('STEM')