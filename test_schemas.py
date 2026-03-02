from pydantic import BaseModel, model_validator, field_validator
import json

class ShiftDefResponse(BaseModel):
    id: int
    name: str
    start_time: str
    end_time: str
    applicable_days: list[int] = [0, 1, 2, 3, 4, 5, 6]

    @model_validator(mode='before')
    @classmethod
    def extract_applicable_days(cls, data):
        if hasattr(data, 'days'):
            days = [d.day_of_week for d in getattr(data, 'days', [])]
            if not days:  # default if no specific days are set
                days = [0, 1, 2, 3, 4, 5, 6]
            if not isinstance(data, dict):
                data.__dict__['applicable_days'] = days
        elif isinstance(data, dict) and 'days' in data:
            days = [d.day_of_week if hasattr(d, 'day_of_week') else d.get('day_of_week') for d in data.get('days', [])]
            if not days:
                days = [0, 1, 2, 3, 4, 5, 6]
            data['applicable_days'] = days
        return data

    @field_validator('applicable_days', mode='before')
    @classmethod
    def parse_applicable_days(cls, v):
        if isinstance(v, str):
            return [int(x) for x in v.split(',') if x.strip()]
        return v

# Test with mock dict
test_data = {
    "id": 1,
    "name": "Poranna",
    "start_time": "07:00",
    "end_time": "15:00",
    "days": []
}

res = ShiftDefResponse(**test_data)
print(f"Data: {test_data}, parsed applicable_days: {res.applicable_days}")

test_data2 = {
    "id": 2,
    "name": "Weekend",
    "start_time": "07:00",
    "end_time": "15:00",
    "days": [{"day_of_week": 5}, {"day_of_week": 6}]
}
res2 = ShiftDefResponse(**test_data2)
print(f"Data: {test_data2}, parsed applicable_days: {res2.applicable_days}")

class MockObj:
    pass

obj = MockObj()
obj.id = 3
obj.name = "Empty Obj"
obj.start_time = "07:00"
obj.end_time = "15:00"
obj.days = []

res3 = ShiftDefResponse.model_validate(obj)
print(f"Obj Data: parsed applicable_days: {res3.applicable_days}")

obj2 = MockObj()
obj2.id = 4
obj2.name = "Obj w/ days"
obj2.start_time = "07:00"
obj2.end_time = "15:00"
class MockDay:
     def __init__(self, d): self.day_of_week = d
obj2.days = [MockDay(0), MockDay(1)]

res4 = ShiftDefResponse.model_validate(obj2)
print(f"Obj2 Data: parsed applicable_days: {res4.applicable_days}")

