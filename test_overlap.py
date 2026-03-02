from datetime import datetime, date, time, timedelta

class MockShift:
    def __init__(self, id, start_time, end_time):
        self.id = id
        self.start_time = start_time
        self.end_time = end_time

shifts = [
    MockShift(1, time(15, 30), time(16, 0)),
    MockShift(2, time(7, 0), time(15, 0)),
    MockShift(3, time(12, 0), time(18, 30)),
]

shift_overlaps = []
for s1 in shifts:
    start1 = datetime.combine(date.today(), s1.start_time)
    end1 = datetime.combine(date.today(), s1.end_time)
    if end1 <= start1: end1 += timedelta(days=1)
    
    for s2 in shifts:
        if s1.id >= s2.id: continue # unique pairs
        
        start2 = datetime.combine(date.today(), s2.start_time)
        end2 = datetime.combine(date.today(), s2.end_time)
        if end2 <= start2: end2 += timedelta(days=1)
        
        # Check overlap: Max(start1, start2) < Min(end1, end2)
        latest_start = max(start1, start2)
        earliest_end = min(end1, end2)
        
        if latest_start < earliest_end:
            overlap_duration = (earliest_end - latest_start).total_seconds() / 60
            is_enveloped = (start1 >= start2 and end1 <= end2) or (start2 >= start1 and end2 <= end1)
            
            if overlap_duration > 30 or is_enveloped:
                shift_overlaps.append((s1.id, s2.id))
                print(f"Overlap {s1.id} & {s2.id}: {overlap_duration} mins, Enveloped: {is_enveloped}")

print("All overlaps:", shift_overlaps)
