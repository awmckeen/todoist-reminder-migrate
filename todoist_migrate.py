import subprocess
import datetime
import os
import argparse
import sys
from todoist_api_python.api import TodoistAPI

# --- CONFIGURATION ---
# Todoist API token: read from environment or provided at runtime
TODOIST_TOKEN = os.environ.get('TODOIST_TOKEN') or ''
# API client will be created at runtime after parsing CLI args or prompting
api = None

# Enable verbose debug output via env or CLI override later
DEBUG = os.environ.get('TODOIST_MIGRATE_DEBUG', '') in ('1', 'true', 'True')
# Dry-run mode (don't call AppleScript) - can be overridden by CLI
DRY_RUN = False

def _get(obj, key):
    """Safely get an attribute or mapping key from obj."""
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)

def create_apple_reminder(name, list_name, description=None, due_date_str=None, priority=1, recurrence_str=None):
    """
    Uses AppleScript to create a new reminder in a specific list.
    If the list does not exist, it creates it automatically.
    """
    # Escape quotes and backslashes to prevent AppleScript syntax errors
    safe_name = name.replace('\\', '\\\\').replace('"', '\\"')
    safe_list_name = list_name.replace('\\', '\\\\').replace('"', '\\"')
    
    # Prepend recurrence info to the notes if it exists
    notes = ""
    if recurrence_str:
        notes += f"[Todoist Recurrence: {recurrence_str}]\n\n"
    if description:
        notes += description
    safe_desc = notes.replace('\\', '\\\\').replace('"', '\\"')
    
    # Map Todoist priority (1: Normal, 4: Urgent) to Apple Reminders priority
    # Apple Reminders: 0 (None), 1 (High), 5 (Medium), 9 (Low)
    rem_priority = 0
    if priority == 4:
        rem_priority = 1
    elif priority == 3:
        rem_priority = 5
    elif priority == 2:
        rem_priority = 9

    applescript = f'''
    tell application "Reminders"
        -- Check if the list exists, create it if it doesn't
        if not (exists list "{safe_list_name}") then
            make new list with properties {{name:"{safe_list_name}"}}
        end if
        
        set targetList to list "{safe_list_name}"
        set reminderProps to {{name:"{safe_name}", body:"{safe_desc}", priority:{rem_priority}}}
    '''
    
    # If a date exists, parse it and add it to the AppleScript properties
    if due_date_str:
        try:
            # due_date_str may already be a date/datetime object from the client
            if isinstance(due_date_str, datetime.datetime):
                dt = due_date_str
            elif isinstance(due_date_str, datetime.date):
                dt = datetime.datetime(due_date_str.year, due_date_str.month, due_date_str.day)
            else:
                if 'T' in due_date_str:
                    dt = datetime.datetime.strptime(due_date_str, "%Y-%m-%dT%H:%M:%SZ")
                else:
                    dt = datetime.datetime.strptime(due_date_str, "%Y-%m-%d")
            
            applescript += f'''
            set theDate to current date
            set year of theDate to {dt.year}
            set month of theDate to {dt.month}
            set day of theDate to {dt.day}
            set time of theDate to { (dt.hour if hasattr(dt, 'hour') else 0) * 3600 + (dt.minute if hasattr(dt, 'minute') else 0) * 60 }

            set reminderProps to reminderProps & {{due date:theDate}}
            '''
        except Exception as e:
            print(f"  [!] Could not parse date for '{name}': {e}")

    # Finish the AppleScript command
    applescript += '''
        make new reminder at end of targetList with properties reminderProps
    end tell
    '''
    
    if DRY_RUN:
        print(f"[DRY-RUN] create reminder in '{list_name}': '{name}' (due={due_date_str}, priority={priority})")
        return

    subprocess.run(['osascript', '-e', applescript], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def migrate_tasks():
    print("Fetching projects from Todoist...")
    try:
        if api is None:
            print("Todoist API client not configured. Aborting.")
            return

        def _flatten(paginator):
            items = []
            for page in paginator:
                if isinstance(page, (list, tuple)):
                    items.extend(page)
                else:
                    items.append(page)
            return items

        projects = _flatten(api.get_projects())
        # Create a dictionary mapping project IDs to their names
        project_map = {}
        for p in projects:
            pid = _get(p, 'id')
            pname = _get(p, 'name') or _get(p, 'title')
            if pid is not None:
                project_map[pid] = pname or 'Inbox'
        
        print("Fetching tasks from Todoist...")
        tasks = _flatten(api.get_tasks())

        if DEBUG:
            print(f"DEBUG: projects returned: {len(projects)}")
            print("DEBUG: project_map sample:", list(project_map.items())[:10])
            print(f"DEBUG: tasks paginator -> list length: {len(tasks)}")
            for i, t in enumerate(tasks[:20]):
                print(f"--- Task #{i} type: {type(t)} ---")
                try:
                    if isinstance(t, dict):
                        print(t)
                    elif isinstance(t, (list, tuple)):
                        print(repr(t))
                    else:
                        # Try to show attributes
                        attrs = {k: getattr(t, k) for k in dir(t) if not k.startswith('_') and not callable(getattr(t, k))}
                        # Trim large values
                        for k in list(attrs.keys()):
                            v = attrs[k]
                            if isinstance(v, (list, tuple)) and len(v) > 5:
                                attrs[k] = f"<{type(v).__name__} len={len(v)}>"
                        print(attrs)
                except Exception as e:
                    print("DEBUG: failed to dump task:", e)
        
        if not tasks:
            print("No active tasks found in Todoist.")
            return

        print(f"Found {len(tasks)} tasks. Migrating to Apple Reminders...\n")

        for task in tasks:
            # Map the task to its project name, default to "Inbox" if no project is found
            proj_id = _get(task, 'project_id')
            list_name = project_map.get(proj_id, 'Inbox')

            due_date = None
            recurrence_str = None

            due = _get(task, 'due')
            if due:
                due_date = _get(due, 'datetime') or _get(due, 'date')
                if _get(due, 'is_recurring') or _get(due, 'recurring'):
                    recurrence_str = _get(due, 'string') or _get(due, 'raw')

            content = _get(task, 'content') or _get(task, 'title') or ''
            description = _get(task, 'description') or ''
            priority = _get(task, 'priority') or 1

            print(f"-> Migrating: [{list_name}] {content}")
            create_apple_reminder(
                name=content,
                list_name=list_name,
                description=description,
                due_date_str=due_date,
                priority=priority,
                recurrence_str=recurrence_str
            )
            
        print("\nSuccess! All tasks have been copied to Apple Reminders.")
        
    except Exception as e:
        print(f"\nAn error occurred: {e}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Migrate Todoist tasks to Apple Reminders')
    parser.add_argument('--token', '-t', help='Todoist API token (overrides TODOIST_TOKEN env)')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    parser.add_argument('--dry-run', action='store_true', help="Don't actually create Reminders; just print actions")
    args = parser.parse_args()

    # Apply CLI options
    if args.debug:
        DEBUG = True
    if args.dry_run:
        DRY_RUN = True

    if args.token:
        TODOIST_TOKEN = args.token.strip()

    if not TODOIST_TOKEN:
        try:
            import getpass
            TODOIST_TOKEN = getpass.getpass("Enter your Todoist API token (input hidden): ").strip()
        except Exception:
            TODOIST_TOKEN = input("Enter your Todoist API token: ").strip()

    if not TODOIST_TOKEN:
        print("No Todoist token provided. The script will abort when attempting to contact the API.")
        api = None
    else:
        try:
            api = TodoistAPI(TODOIST_TOKEN)
        except Exception as e:
            print(f"Failed to create Todoist client: {e}")
            api = None

    migrate_tasks()