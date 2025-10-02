# Daily Loss Rule Implementation
# Monitors cumulative realized P&L; breaches if < -max_usd, triggers kill switch.

async def check(event, config, suite=None, dry_run=False, daily_pnl=0.0):
    if not config.get('enabled', False):
        return {'status': 'VALID', 'reason': '', 'action': ''}
    
    max_usd = config['parameters'].get('max_usd', 200)
    event_pnl = 0.0
    if event.type == EventType.POSITION_CLOSED:
        event_pnl = event.data.get('pnl', 0.0)
    elif event.type == EventType.POSITION_PNL_UPDATE:
        event_pnl = event.data.get('realized_pnl', 0.0)
    
    if event_pnl == 0.0:
        return {'status': 'VALID', 'reason': '', 'action': ''}
    
    projected_pnl = daily_pnl + event_pnl
    if projected_pnl < -max_usd:
        reason = f'Daily realized P&L {projected_pnl:.2f} < -{max_usd:.2f}'
        return {
            'status': 'BREACH',
            'reason': reason,
            'action': 'kill_switch'
        }
    
    return {'status': 'VALID', 'reason': '', 'action': ''}


