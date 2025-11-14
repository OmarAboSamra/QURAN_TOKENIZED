"""Quick stats check for root extraction."""
from backend.db import get_sync_session_maker
from backend.models import Token

session = get_sync_session_maker()()

total = session.query(Token).count()
with_roots = session.query(Token).filter(Token.root.isnot(None)).count()
coverage = (with_roots/total)*100 if total > 0 else 0

print(f'Total tokens: {total}')
print(f'Tokens with roots: {with_roots}')
print(f'Coverage: {coverage:.1f}%')
print(f'\nBy Sura:')

for sura in [1, 2]:
    sura_total = session.query(Token).filter(Token.sura == sura).count()
    sura_roots = session.query(Token).filter(Token.sura == sura, Token.root.isnot(None)).count()
    if sura_total > 0:
        print(f'  Sura {sura}: {sura_roots}/{sura_total} ({(sura_roots/sura_total*100):.1f}%)')

session.close()
