import argparse
from app import app
from stoic_db import migrate


def main():
    parser = argparse.ArgumentParser(description='STOIQ operations. Never prints secrets or private records.')
    parser.add_argument('command', choices=['migrate', 'import-become'])
    parser.add_argument('--source', help='Read-only path to the old BECOME SQLite database')
    parser.add_argument('--username', help='Existing STOIQ account that owns the imported records')
    args = parser.parse_args()
    migrate(app.config)
    if args.command == 'migrate':
        print('STOIQ migrations applied. Existing tables and records were not dropped.')
    else:
        if not args.source or not args.username:
            parser.error('import-become requires --source and --username')
        from import_become import import_records
        with app.app_context():
            count = import_records(args.source, args.username)
        print(f'Imported {count} challenges. Existing imports were skipped; source database unchanged.')


if __name__ == '__main__':
    main()
