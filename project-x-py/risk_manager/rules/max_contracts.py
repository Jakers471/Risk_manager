import json
from datetime import datetime
from project_x_py import EventType

async def check(event, config, suite=None, dry_run=False, daily_pnl=0.0):  # Ignore daily_pnl for this rule
    if config.get('enabled', False):
        max_size = config['parameters'].get('max_contracts', 4)
        
        if event.type == EventType.POSITION_UPDATED:
            size = abs(event.data.get('size', 0))
            if size > max_size:
                return {
                    'status': 'BREACH',
                    'reason': f'Net position size {size} exceeds max {max_size}',
                    'action': 'flatten'
                }
            return {
                'status': 'VALID',
                'reason': '',
                'action': ''
            }
        elif event.type == EventType.ORDER_FILLED:
            order = event.data.get('order')
            if order:
                fill_size = abs(getattr(order, 'size', 0)) if hasattr(order, 'size') else 0
                side = getattr(order, 'side', 0) if hasattr(order, 'side') else 0
                contract_id = getattr(order, 'contractId', None) if hasattr(order, 'contractId') else None
                symbol = 'MNQ'  # Default
                
                if suite and fill_size > 0:
                    try:
                        # Use contract_id if available, else fallback symbol
                        if contract_id:
                            current_pos = await suite.positions.get_position(contract_id)
                        else:
                            current_pos = await suite.positions.get_position(symbol)
                        current_size = getattr(current_pos, 'size', 0) if current_pos else 0
                        print(f"Debug: Query with contract_id={contract_id}, current_size={current_size}")  # Temp
                        delta = fill_size if side == 0 else -fill_size
                        net_size = current_size + delta
                        if abs(net_size) > max_size:
                            reason = f'Projected net position size {abs(net_size)} exceeds max {max_size}'
                            return {
                                'status': 'BREACH',
                                'reason': reason,
                                'action': 'flatten'
                            }
                        return {
                            'status': 'VALID',
                            'reason': '',
                            'action': ''
                        }
                    except Exception as e:
                        print(f"Query failed for {contract_id or symbol}: {e}")  # Temp debug
                        # Fallback: Breach on large fill (conservative)
                        if fill_size > max_size:
                            reason = f'Dry-run fill size {fill_size} exceeds max {max_size}' if dry_run else f'Fill size {fill_size} exceeds max {max_size} (query failed)'
                            return {
                                'status': 'BREACH',
                                'reason': reason,
                                'action': 'flatten'
                            }
                        return {
                            'status': 'VALID',
                            'reason': '',
                            'action': ''
                        }
                # No suite: Fallback
                if fill_size > max_size:
                    reason = f'Dry-run fill size {fill_size} exceeds max {max_size}' if dry_run else f'Fill size {fill_size} exceeds max {max_size}'
                    return {
                        'status': 'BREACH',
                        'reason': reason,
                        'action': 'flatten'
                    }
                print(f"Debug: Dry-run fallback - fill_size={fill_size}, side={side}, VALID")
        
        return {
            'status': 'VALID',
            'reason': '',
            'action': ''
        }