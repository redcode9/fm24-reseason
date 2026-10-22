"""Portable DRAFT runtime with one manifest-pinned Ahron retention DDT.

Separate from frozen schema2 tools. Transactions cover listed own FMFs, the
explicit Basic Italy replacement, and one named 28-byte extra-data text file.
No executable, native DB binary, other extra-data file or save is written.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import subprocess
import sys
import uuid

sys.dont_write_bytecode = True
PACK_ID = 'fm24-history-community-mac-arm64'
STATE_DIR = 'FM24-History-Community'
SHA = re.compile(r'^[0-9a-f]{64}$')
OWN_NAME = re.compile(r'^FM24_2026_27_[A-Za-z0-9_]+\.fmf$')
BASIC_ITALY = 'sortitoutsi.net FM24 Data Update - Italy (2026 Start).fmf'
DDT_NAME = 'FM24_History_Ahron_Retention.ddt'
DDT_PAYLOAD = 'payload/extra_data/' + DDT_NAME
DDT_STEAM_RELATIVE = 'data/database/db/2430/edt/permanent/' + DDT_NAME
DDT_CONTENT = b'"RETAIN_PLAYERS" "71046777"\n'
DDT_SHA = 'c905f925e6432036beb2e2cc4ab82f8e12292c4a40a916a0351d29d6b965ed76'
ENV_NAMES = ('DYLD_INSERT_LIBRARIES', 'FM24_AWARDS_LOG', 'FM24_AWARDS_SCHEDULE_MODE',
             'FM24_AWARDS_FIRST_CYCLE_MODE', 'FM24_COMP_HISTORY_PROBE',
             'FM24_WORLD_CUP_HISTORY_MODE', 'FM24_INTERNATIONAL_HISTORY_MODE',
             'FM24_INTERNATIONAL6_HISTORY_MODE')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()


def relative_path(value):
    require(isinstance(value, str) and value and '\\' not in value and ':' not in value and '\x00' not in value,
            'Invalid relative path')
    path = PurePosixPath(value)
    require(not path.is_absolute() and all(p not in {'', '.', '..'} for p in value.split('/')),
            'Absolute/traversal path refused')
    return Path(*path.parts)


def own_name(value):
    require(isinstance(value, str) and OWN_NAME.fullmatch(value), 'Not an explicit owned FMF basename')
    require(not any(t in value.upper() for t in ('TEST', 'DIAGNOSTICA', 'PROBE')), 'Test/probe FMFs are not release payload')
    return value


def confined(root, relative):
    root = Path(root).absolute()
    require(not root.is_symlink(), 'Symlink root refused')
    current = root
    for part in relative_path(relative).parts:
        current = current / part
        require(not current.is_symlink(), 'Symlink destination/source refused: ' + relative)
    require(current.resolve().is_relative_to(root.resolve()), 'Path escapes selected root')
    return current


def validate_policy(data):
    """Validate a closed selection without touching any installation."""
    require(data.get('schema') in {2,3} and data.get('pack_id') == PACK_ID and data.get('status') == 'DRAFT', 'Wrong package schema/identity')
    require(data.get('readiness', {}).get('state') == 'PENDING_EXACT_PACK_CAREER_AND_COLD_TEST', 'DRAFT readiness cannot inherit old gameplay')
    require(data['snapshot'].get('world_complete') is False and data['snapshot'].get('official_FM27') is False, 'Unsupported coverage claim')
    paths = set()
    for item in data['files']:
        relative_path(item['path'])
        require(item['path'].casefold() not in paths, 'Duplicate package path')
        paths.add(item['path'].casefold())
        require(SHA.fullmatch(item['sha256']) and type(item['bytes']) is int and item['bytes'] > 0, 'Invalid file pin')
    declared = {item['path']:item for item in data['files']}
    retention = data.get('retention_ddt', [])
    require(len(retention) <= 1 and (not retention or data['schema'] == 3), 'One schema3 retention DDT only')
    for row in retention:
        require(row['name'] == DDT_NAME and row['payload'] == DDT_PAYLOAD and row['steam_relative'] == DDT_STEAM_RELATIVE,
                'Only the explicit owned DB24.3 retention DDT path is supported')
        require(row['sha256'] == DDT_SHA and row['bytes'] == len(DDT_CONTENT), 'Retention DDT must be exact Ahron one-line source')
        require(row['payload'] in declared and declared[row['payload']]['sha256'] == DDT_SHA and declared[row['payload']]['bytes'] == len(DDT_CONTENT), 'Retention DDT payload not pinned')
        require(all(SHA.fullmatch(s) for s in row.get('previous_sha256', [])), 'Invalid previous DDT SHA')
    names = set(); slots = set(); current = {}
    for row in data['own_fmfs']:
        own_name(row['name'])
        require(row['name'].casefold() not in names, 'Duplicate/case-colliding owned FMF')
        names.add(row['name'].casefold())
        require(re.fullmatch(r'[a-z0-9_]+', row['slot']) and row['slot'] not in slots, 'Duplicate/invalid active logical slot')
        slots.add(row['slot']);current[row['name']] = row
        require(row['payload'] == 'payload/editor data/' + row['name'], 'Owned payload path differs from basename')
        require(row['payload'] in declared and declared[row['payload']]['sha256'] == row['sha256'], 'Unpinned FMF payload')
        require(all(SHA.fullmatch(s) for s in row.get('previous_sha256', [])), 'Invalid prior owned SHA')
    aliases = data.get('filename_aliases', {})
    require(isinstance(aliases, dict) and all(isinstance(n, str) for n in aliases.values()),
            'Invalid filename alias catalogue')
    if aliases:
        require(set(aliases) == set(current), 'Filename aliases must cover exactly the owned FMFs')
        ordered = [aliases[name] for name in sorted(current)]
        require(len({name.casefold() for name in ordered}) == len(ordered), 'Duplicate filename alias')
        for number, name in enumerate(ordered, 1):
            require(isinstance(name, str) and re.fullmatch(
                rf"ReSeason 2026-27 - {number:02d} - [A-Za-z0-9][A-Za-z0-9 .()+'-]*\.fmf", name),
                'Invalid filename alias or changed alphabetical order')
        require(not {name.casefold() for name in ordered} & names, 'Filename alias overlaps canonical names')
    updates = data.get('filename_updates', {})
    require(isinstance(updates, dict), 'Invalid filename metadata catalogue')
    if updates:
        require(aliases and set(updates) == set(current), 'Filename metadata must cover the owned aliases')
        for name, update in updates.items():
            original = declared[current[name]['payload']]
            require(update['before_sha256'] == original['sha256'] and update['before_bytes'] == original['bytes'],
                    'Filename metadata differs from canonical payload pin')
            require(SHA.fullmatch(update['after_sha256']) and type(update['offset']) is int and
                    0 < update['offset'] < update['before_bytes'] and type(update['after_bytes']) is int,
                    'Invalid filename metadata bounds or digest')
            for side in ('before', 'after'):
                tail = bytes.fromhex(update[side + '_tail_hex'])
                require(0 < len(tail) <= 65536 and update[side + '_bytes'] == update['offset'] + len(tail),
                        'Filename metadata trailer size differs')
    for row in data.get('retire_owned', []):
        own_name(row['name'])
        require(row['name'].casefold() not in names and row['allowed_sha256'], 'Retire/current ownership overlap')
        names.add(row['name'].casefold())
        require(all(SHA.fullmatch(s) for s in row['allowed_sha256']), 'Invalid retired owned SHA')
    require(len(data['basic_catalogue']) == 54, 'External Basic54 source catalogue is incomplete')
    basic_names = set()
    catalogue = {}
    for row in data['basic_catalogue']:
        require(Path(row['name']).name == row['name'] and row['name'].startswith('sortitoutsi.net FM24 Data Update - '), 'Invalid Basic dependency basename')
        require(row['name'].endswith('.fmf') and row['name'].casefold() not in basic_names and SHA.fullmatch(row['sha256']) and type(row['bytes']) is int and row['bytes'] > 0, 'Duplicate/invalid Basic dependency')
        basic_names.add(row['name'].casefold());catalogue[row['name']] = row
    require(not basic_names & names, 'Owned files overlap Basic')
    replacements = data.get('basic_replacements', [])
    require(len(replacements) <= 1, 'Only the single explicit Italy Basic replacement is supported')
    for row in replacements:
        require(row['dependency_name'] == BASIC_ITALY and row['dependency_name'] in catalogue, 'Only pinned Basic Italy can be replaced')
        original = catalogue[row['dependency_name']]
        require(row['dependency_sha256'] == original['sha256'] and row['dependency_bytes'] == original['bytes'], 'Italy replacement pin differs from Basic origin')
        require(row['replacement_name'] in current and current[row['replacement_name']]['slot'] == 'italy_rules', 'Italy replacement must select the explicit italy_rules slot')
    require(bool(replacements) == ('italy_rules' in slots), 'Italy rule overlay refused; explicit Basic replacement required')
    expected = [r for r in data['basic_catalogue'] if r['name'] not in {x['dependency_name'] for x in replacements}]
    require(data['external_basic'] == expected, 'Active external Basic dependencies are not origin minus explicit replacement')
    for group in data.get('exclusive_replacements', []):
        require(group['selected_name'] in current and current[group['selected_name']]['slot'] == group['slot'], 'Exclusive slot selection differs')
        old = group.get('superseded_names', [])
        require(all(n not in current for n in old), 'Superseded file still selected')
        retired = {r['name'] for r in data.get('retire_owned', [])}
        require(set(old).issubset(retired), 'Superseded name lacks explicit pinned retirement')
    require(data['snapshot']['own_FMFs'] == len(current) and data['snapshot']['Basic_external_FMFs'] == len(expected) and data['snapshot']['total_active_FMFs'] == len(current) + len(expected), 'Dynamic selection counts differ')
    require(data['module']['path'] in declared and declared[data['module']['path']]['sha256'] == data['module']['sha256'], 'Module not pinned')
    require(SHA.fullmatch(data['game']['executable_sha256']), 'Exact game SHA missing')


def package(root, expected_sha=None):
    root = Path(root).absolute()
    manifest_file = confined(root, 'release.json')
    seal = confined(root, 'RELEASE_MANIFEST.sha256').read_text().strip()
    require(SHA.fullmatch(seal), 'Invalid manifest pin')
    require(expected_sha is None or seal == expected_sha, 'Manifest differs from requested pin')
    require(digest(manifest_file) == seal, 'Manifest SHA mismatch')
    data = json.loads(manifest_file.read_bytes())
    validate_policy(data)
    for item in data['files']:
        path = confined(root, item['path'])
        require(path.is_file() and path.stat().st_size == item['bytes'] and digest(path) == item['sha256'], 'Package file pin mismatch: ' + item['path'])
    for row in data.get('retention_ddt', []):
        require(confined(root,row['payload']).read_bytes() == DDT_CONTENT, 'Retention DDT has extra commands or differs from one-line source')
    return data, seal


def basic_status(data, user_data):
    rows = []
    for row in data['external_basic']:
        path = confined(user_data, 'editor data/' + row['name'])
        actual = digest(path) if path.is_file() else None
        rows.append({'name':row['name'], 'expected':row['sha256'], 'actual':actual, 'match':actual == row['sha256']})
    return {'files':rows, 'matches':sum(r['match'] for r in rows), 'complete':all(r['match'] for r in rows)}


def load_state(user_data):
    path = confined(user_data, STATE_DIR + '/owned_state.json')
    if not path.exists():
        return None
    data = json.loads(path.read_bytes())
    require(data.get('pack_id') == PACK_ID and data.get('schema') == 1, 'Different owner of install receipt directory')
    for name, sha in data['owned'].items():
        own_name(name); require(SHA.fullmatch(sha), 'Invalid installed ownership receipt')
    for path, sha in data.get('ddt_owned', {}).items():
        require(path == DDT_STEAM_RELATIVE and SHA.fullmatch(sha), 'Invalid DDT ownership receipt')
    return data


def default_steam_game():
    return Path.home()/'Library/Application Support/Steam/steamapps/common/Football Manager 2024'


def target_path(user_data, steam_game, row):
    if row.get('kind') == 'retention_ddt':
        require(row['name'] == DDT_NAME and row['steam_relative'] == DDT_STEAM_RELATIVE, 'Unlisted extra-data destination')
        return confined(steam_game, DDT_STEAM_RELATIVE)
    return confined(user_data, 'editor data/' + row['name'])


def installed_fmf(data, user_data, name):
    """Receipts use canonical identities; the installed basename may be readable."""
    canonical = confined(user_data, 'editor data/' + name)
    alias = data.get('filename_aliases', {}).get(name)
    if alias is None:
        return canonical
    readable = confined(user_data, 'editor data/' + alias)
    require(not (canonical.exists() and readable.exists()), 'Both canonical and readable copies of one FMF are installed')
    return readable if readable.exists() else canonical


def installation_plan(root, user_data, expected_sha=None, steam_game=None):
    data, seal = package(root, expected_sha)
    user_data = Path(user_data).absolute()
    steam_game = Path(steam_game or default_steam_game()).absolute()
    confined(user_data, 'editor data')
    state = load_state(user_data)
    before_owned = state['owned'] if state else {}
    new = {r['name']:r for r in data['own_fmfs']}
    retired = {r['name']:r for r in data.get('retire_owned', [])}
    unaccounted = set(before_owned) - set(new) - set(retired)
    require(not unaccounted, 'Update omits prior owned files without explicit retire entries: ' + ','.join(sorted(unaccounted)))
    actions = []
    for name, row in new.items():
        target = installed_fmf(data, user_data, name)
        require(not target.exists() or target.is_file(), 'Owned destination is not a regular file')
        actual = digest(target) if target.is_file() else None
        allowed = set(row.get('previous_sha256', [])) | {before_owned.get(name)}
        exact = {row['sha256']}
        if name in data.get('filename_updates', {}):
            exact.add(data['filename_updates'][name]['after_sha256'])
        require(actual in {None} | exact or actual in allowed, 'Unknown local version at owned filename; pinned previous SHA required: ' + name)
        kind = 'keep' if actual in exact else 'create' if actual is None else 'replace'
        actions.append({'name':name, 'action':kind, 'before_sha256':actual, 'after_sha256':row['sha256'], 'payload':row['payload']})
    for name, row in retired.items():
        target = confined(user_data, 'editor data/' + name)
        actual = current_sha(target)
        allowed = set(row['allowed_sha256']) | {before_owned.get(name)}
        require(actual is None or actual in allowed, 'Unknown retired version refused: ' + name)
        actions.append({'name':name, 'action':'retire' if actual else 'absent', 'before_sha256':actual, 'after_sha256':None})
    for row in data.get('basic_replacements', []):
        name = row['dependency_name'];target = confined(user_data, 'editor data/' + name)
        actual = current_sha(target)
        require(actual is None or actual == row['dependency_sha256'], 'Unknown Basic Italy variant preserved; exact replacement pin required')
        actions.append({'name':name, 'action':'retire' if actual else 'absent', 'before_sha256':actual, 'after_sha256':None,
                        'kind':'replaced_external_basic', 'authorised_original_sha256':row['dependency_sha256'],
                        'replacement_name':row['replacement_name']})
    previous_ddt = state.get('ddt_owned', {}) if state else {}
    after_ddt = {r['steam_relative']:r['sha256'] for r in data.get('retention_ddt', [])}
    require(set(previous_ddt) <= set(after_ddt), 'Update omits previously owned DDT; preserve it with an explicit manifest entry')
    for row in data.get('retention_ddt', []):
        target = target_path(user_data,steam_game,row | {'kind':'retention_ddt'})
        # This known installed extra-data root must already exist. No arbitrary
        # directory trees are created below a guessed game path.
        require(target.parent.is_dir(), 'DB24.3 extra-data edt/permanent directory missing')
        actual = current_sha(target)
        allowed = set(row.get('previous_sha256', [])) | {previous_ddt.get(row['steam_relative'])}
        require(actual in {None,row['sha256']} or actual in allowed, 'Unknown local DDT version preserved; exact previous SHA required')
        actions.append({'kind':'retention_ddt','name':row['name'],'steam_relative':row['steam_relative'],
                        'action':'keep' if actual==row['sha256'] else 'create' if actual is None else 'replace',
                        'before_sha256':actual,'after_sha256':row['sha256'],'payload':row['payload']})
    dependency = basic_status(data, user_data)
    own_dir = confined(user_data, STATE_DIR + '/transactions')
    unfinished = []
    if own_dir.exists():
        for path in own_dir.glob('*/journal.json'):
            require(not path.is_symlink() and not path.parent.is_symlink(), 'Symlink transaction refused')
            journal = json.loads(path.read_bytes())
            if journal.get('status') not in {'COMMITTED','ROLLED_BACK'}:unfinished.append(path.parent.name)
    return {'status':'DRY_RUN_NO_WRITES', 'pack_id':PACK_ID, 'release_id':data['release_id'],
            'manifest_sha256':seal, 'actions':actions, 'Basic54':dependency,
            'external_Basic_source_count':len(data['basic_catalogue']),'external_Basic_active_count':len(data['external_basic']),
            'Italy_replacement_no_overlay':bool(data.get('basic_replacements')),
            'unfinished_transactions':unfinished, 'ready':dependency['complete'] and not unfinished,
            'prior_state':state, 'after_owned':{n:r['sha256'] for n,r in new.items()},
            'after_ddt_owned':after_ddt,'steam_game_root':str(steam_game),
            'writes_only_listed_FMFs_DDT_and_receipts':True,
            'retention_DDT_native_consumption_proven':False}


def atomic_json(path, data):
    temporary = path.with_name(path.name + '.new')
    require(not temporary.is_symlink(), 'Symlink journal temp refused')
    with temporary.open('wb') as handle:
        handle.write(encoded(data));handle.flush();os.fsync(handle.fileno())
    os.replace(temporary, path)


@contextmanager
def locked(user_data):
    import fcntl
    folder = confined(user_data, STATE_DIR)
    folder.mkdir(parents=True, exist_ok=True)
    path = confined(user_data, STATE_DIR + '/install.lock')
    with path.open('a+b') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield folder


def current_sha(path):
    require(not path.exists() or path.is_file(), 'Non-file owned destination')
    return digest(path) if path.is_file() else None


def restore_journal(user_data, transaction_id, steam_game=None):
    require(re.fullmatch(r'[0-9a-f]{32}', transaction_id), 'Invalid transaction ID')
    folder = confined(user_data, STATE_DIR + '/transactions/' + transaction_id)
    journal = json.loads(confined(folder, 'journal.json').read_bytes())
    require(journal.get('pack_id') == PACK_ID and journal.get('transaction_id') == transaction_id, 'Unbound transaction journal')
    steam_game = Path(steam_game or default_steam_game()).absolute()
    if any(row.get('kind') == 'retention_ddt' for row in journal['actions']):
        require(journal.get('steam_game_root') == str(steam_game), 'Recovery game root differs from the DDT transaction')
    if journal['status'] == 'ROLLED_BACK':return {'status':'ROLLED_BACK','already_done':True}
    for row in reversed(journal['actions']):
        if row.get('kind') == 'retention_ddt':
            require(row['name'] == DDT_NAME and row['after_sha256'] == DDT_SHA and row['steam_relative'] == DDT_STEAM_RELATIVE,
                    'Unbound retention DDT recovery')
        elif row.get('kind') == 'replaced_external_basic':
            require(row['name'] == BASIC_ITALY and SHA.fullmatch(row['authorised_original_sha256']) and row['before_sha256'] == row['authorised_original_sha256'] and row['after_sha256'] is None, 'Unbound external replacement recovery')
            own_name(row['replacement_name'])
        else:own_name(row['name'])
        target = target_path(user_data,steam_game,row)
        actual = current_sha(target)
        before, after = row['before_sha256'], row['after_sha256']
        require(actual in {before,after}, 'Concurrent local edit preserved; cannot restore: ' + row['name'])
        if actual == before:continue
        if before is None:
            if target.exists():target.unlink()
        else:
            backup = confined(folder, 'backup/' + row['name'])
            require(backup.is_file() and digest(backup) == before, 'Backup missing/changed')
            restore = confined(folder, 'restore_' + row['name'])
            shutil.copyfile(backup, restore);os.replace(restore, target)
    state = confined(user_data, STATE_DIR + '/owned_state.json')
    if journal['prior_state'] is not None:atomic_json(state, journal['prior_state'])
    elif state.exists():state.unlink()
    journal['status'] = 'ROLLED_BACK';atomic_json(folder/'journal.json', journal)
    return {'status':'ROLLED_BACK','transaction_id':transaction_id,'backup_files_preserved':True}


def apply_install(root, user_data, expected_sha=None, fault_after=None, steam_game=None):
    """Only called with --apply; fault_after is test-only and not a CLI option."""
    require(platform.system()=='Darwin' and platform.machine()=='arm64','Only macOS arm64 is supported')
    steam_game = Path(steam_game or default_steam_game()).absolute()
    plan = installation_plan(root, user_data, expected_sha,steam_game)
    require(plan['ready'], 'Basic dependencies mismatch/missing or unfinished transaction; no FMFs changed')
    data,_ = package(root,expected_sha)
    require(not data.get('filename_aliases'),
            'The legacy write installer does not support filename aliases; use the public manual placement and organize command')
    binary = game_binary(steam_game)
    require(binary.is_file() and digest(binary)==data['game']['executable_sha256'],'Exact supported FM24 executable SHA required before install')
    mutations = [r for r in plan['actions'] if r['action'] in {'create','replace','retire'}]
    state = {'schema':1,'pack_id':PACK_ID,'release_id':plan['release_id'],
             'manifest_sha256':plan['manifest_sha256'],'owned':plan['after_owned'],'ddt_owned':plan['after_ddt_owned']}
    with locked(user_data) as owned:
        fresh = installation_plan(root, user_data, expected_sha,steam_game)
        require(fresh == plan, 'Install changed after planning; no FMFs changed')
        if not mutations:
            previous = load_state(user_data)
            if previous != state:atomic_json(owned/'owned_state.json', state)
            return {'status':'ALREADY_INSTALLED','changed_FMFs':0,'changed_DDTs':0,'backups_created':0}
        transaction_id = uuid.uuid4().hex
        folder = confined(user_data, STATE_DIR + '/transactions/' + transaction_id)
        (folder/'backup').mkdir(parents=True);(folder/'stage').mkdir()
        journal = {'schema':1,'pack_id':PACK_ID,'transaction_id':transaction_id,'status':'PREPARING',
                   'manifest_sha256':plan['manifest_sha256'],'actions':mutations,'prior_state':plan['prior_state'],
                   'steam_game_root':str(steam_game)}
        atomic_json(folder/'journal.json', journal)
        try:
            for row in mutations:
                target = target_path(user_data,steam_game,row)
                require(current_sha(target) == row['before_sha256'], 'Target changed before backup')
                if row['before_sha256']:
                    backup = folder/'backup'/row['name'];shutil.copyfile(target, backup)
                    require(digest(backup) == row['before_sha256'], 'Backup hash mismatch')
                if row['after_sha256']:
                    source = confined(root, row['payload']);staged = folder/'stage'/row['name']
                    shutil.copyfile(source, staged);os.chmod(staged, 0o644)
                    require(digest(staged) == row['after_sha256'], 'Staged FMF hash mismatch')
            journal['status'] = 'PREPARED';atomic_json(folder/'journal.json', journal)
            confined(user_data, 'editor data').mkdir(parents=True, exist_ok=True)
            for index, row in enumerate(mutations, 1):
                target = target_path(user_data,steam_game,row)
                require(current_sha(target) == row['before_sha256'], 'Concurrent target change; rollback required')
                if row['action'] == 'retire':target.unlink()
                else:os.replace(folder/'stage'/row['name'], target)
                require(current_sha(target) == row['after_sha256'], 'Installed FMF hash mismatch')
                if fault_after == index:raise RuntimeError('SIMULATED_TRANSACTION_FAILURE')
            atomic_json(owned/'owned_state.json', state)
            journal['status'] = 'COMMITTED';atomic_json(folder/'journal.json', journal)
        except Exception:
            restore_journal(user_data, transaction_id,steam_game)
            raise
    return {'status':'INSTALLED','changed_FMFs':sum(r.get('kind')!='retention_ddt' for r in mutations),
            'changed_DDTs':sum(r.get('kind')=='retention_ddt' for r in mutations),
            'backups_created':sum(bool(r['before_sha256']) for r in mutations),'transaction_id':transaction_id,
            'external_Basic_active_count':len(data['external_basic'])}


def game_binary(steam_game):
    return Path(steam_game)/'fm.app/Contents/MacOS/fm'


def launch_plan(root, steam_game, user_data, mode, expected_sha=None):
    require(mode in {'initialise','cold'}, 'Unknown launch mode')
    data, seal = package(root, expected_sha)
    require(platform.system() == 'Darwin' and platform.machine() == 'arm64', 'Only macOS arm64 is supported')
    binary = game_binary(steam_game)
    require(binary.is_file() and digest(binary) == data['game']['executable_sha256'], 'Exact supported FM24 executable SHA required')
    installed = installation_plan(root, user_data, expected_sha,steam_game)
    require(installed['Basic54']['complete'] and not installed['unfinished_transactions'], 'Installation dependencies incomplete')
    require(all(a['action'] in {'keep','absent'} for a in installed['actions']), 'Listed own FMFs not installed at exact release hashes')
    if data.get('filename_aliases'):
        readable = sum(installed_fmf(data, user_data, row['name']).name != row['name'] for row in data['own_fmfs'])
        require(readable in {0, len(data['own_fmfs'])}, 'Finish organizing the complete filename set before launch')
    if data.get('filename_updates'):
        updates = data['filename_updates']
        retitled = sum(action['name'] in updates and action['before_sha256'] == updates[action['name']]['after_sha256']
                       for action in installed['actions'])
        require(retitled in {0, len(updates)}, 'Finish organizing the complete internal-title set before launch')
    require(data['module'].get('international6_mode') == 'skip-completed', 'The exact bounded skip-completed module is required')
    env = {name:'' for name in ENV_NAMES}
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')
    logs = confined(user_data, STATE_DIR + '/logs')
    if mode == 'initialise':
        env.update(DYLD_INSERT_LIBRARIES=str(confined(root,data['module']['path'])),
                   FM24_AWARDS_LOG=str(logs/('module_'+stamp+'.log')),
                   FM24_AWARDS_SCHEDULE_MODE='apply',FM24_AWARDS_FIRST_CYCLE_MODE='catchup',
                   FM24_WORLD_CUP_HISTORY_MODE='skip-completed',FM24_INTERNATIONAL_HISTORY_MODE='skip-completed',
                   FM24_INTERNATIONAL6_HISTORY_MODE='skip-completed')
    env.update(SteamAppId='2252570', SteamGameId='2252570')
    command = ['open','-n']
    for key,value in env.items():command.extend(['--env',key+'='+value])
    command.extend(['--stdout',str(logs/('game_'+stamp+'.log')),'--stderr',str(logs/('game_'+stamp+'.log')),str(binary.parents[2])])
    return {'status':'DRY_RUN_NO_GAME_LAUNCHED','mode':mode,'manifest_sha256':seal,
            'library_injected':mode == 'initialise','environment':env,'command':command,
            'logs_directory':str(logs),'writes_to_installed_executable_DB_or_saves':False}


def main(action, root=None, argv=None):
    root = Path(root or Path(__file__).resolve().parent)
    parser = argparse.ArgumentParser(description='FM24 FREE COMMUNITY DRAFT — offline, Mac arm64 only')
    parser.add_argument('--user-data',type=Path,default=Path.home()/'Library/Application Support/Sports Interactive/Football Manager 2024')
    parser.add_argument('--manifest-sha256')
    parser.add_argument('--steam-game',type=Path,default=Path.home()/'Library/Application Support/Steam/steamapps/common/Football Manager 2024')
    if action == 'install':
        parser.add_argument('--apply',action='store_true')
        parser.add_argument('--recover',metavar='TRANSACTION_ID')
    else:
        parser.add_argument('--mode',choices=['initialise','cold'],default='cold')
        parser.add_argument('--run',action='store_true')
    args = parser.parse_args(argv)
    if action == 'install':
        if args.recover:
            require(args.apply, '--recover requires --apply; default remains read-only')
            require(platform.system()=='Darwin' and platform.machine()=='arm64','Only macOS arm64 is supported')
            require(subprocess.run(['pgrep','-x','fm'],capture_output=True).returncode==1,'FM must be closed for recovery')
            with locked(args.user_data):result=restore_journal(args.user_data,args.recover,args.steam_game)
        elif args.apply:
            require(platform.system()=='Darwin' and platform.machine()=='arm64','Only macOS arm64 is supported')
            require(subprocess.run(['pgrep','-x','fm'],capture_output=True).returncode==1,'FM must be closed before changing owned FMFs')
            result=apply_install(root,args.user_data,args.manifest_sha256,steam_game=args.steam_game)
        else:
            result=installation_plan(root,args.user_data,args.manifest_sha256,args.steam_game)
            data,_=package(root,args.manifest_sha256);binary=game_binary(args.steam_game)
            actual=digest(binary) if binary.is_file() else None
            result['game_build_SHA_match']=actual==data['game']['executable_sha256']
            result['ready']=result['ready'] and result['game_build_SHA_match']
    else:
        result=launch_plan(root,args.steam_game,args.user_data,args.mode,args.manifest_sha256)
        if args.run:
            require(subprocess.run(['pgrep','-x','fm'],capture_output=True).returncode==1,'FM is already open')
            Path(result['logs_directory']).mkdir(parents=True,exist_ok=True)
            subprocess.run(result['command'],check=True)
            result['status']='LAUNCH_REQUESTED_GAMEPLAY_NOT_CERTIFIED'
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    raise SystemExit('Use the supplied install.py or launch.py entry point')
