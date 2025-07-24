import json

# 데이터 크기 기준 분할 함수

MAX_EVENT_SIZE = 250_000

def split_items_by_size(item_list, max_size=MAX_EVENT_SIZE):
    chunks = []
    current_chunk = []
    current_size = 0

    for record in item_list:
        record_str = json.dumps(record, ensure_ascii=False)
        record_size = len(record_str.encode('utf-8'))

        if current_size + record_size > max_size:
            chunks.append(current_chunk)
            current_chunk = [record]
            current_size = record_size
        else:
            current_chunk.append(record)
            current_size += record_size

    if current_chunk:
        chunks.append(current_chunk)

    return chunks