import json
from datetime import datetime
from project_x_py import EventType  # Add this line

def check(event, config):
    if config.get('enabled', False):
        size = 0
        if event.type == EventType.POSITION_UPDATED:
            size = abs(event.data.get('size', 0))
        elif event.type == EventType.ORDER_FILLED:
            if 'order' in event.data:
                order = event.data['order']
                size = abs(order.size)
        
        max_size = config['parameters'].get('max_contracts', 4)
        if size > max_size:
            return {
                'status': 'BREACH',
                'reason': f'Position size {size} exceeds max {max_size}',
                'action': 'flatten'
            }
    return {
        'status': 'VALID',
        'reason': '',
        'action': ''
    }