class Weekdays:
    def __init__(self, day):
        self.day = str(day)

    def is_weekend(self):
        return self.day.lower() in ['sunday', 'cn', 'chủ nhật']
    def is_weekday(self):
        return self.day in ['2', '3', '4', '5', '6', '7']