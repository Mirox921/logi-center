"""Private reusable macro library stored in the existing DraftStore."""
from copy import deepcopy
import uuid
from mouse_models import validate_macro

KEY='macro-library:v1'


def load(store):
    entries,unused=store.get(KEY,[])
    try:
        if not isinstance(entries,list) or len(entries)>100:raise ValueError('Invalid library')
        result=[];seen=set()
        for entry in entries:
            if not isinstance(entry,dict) or set(entry)-{'id','name','tokens','repeat_mode'} or not {'id','name','tokens'}<=set(entry):raise ValueError('Invalid entry')
            if entry.get('repeat_mode','once') not in ('once','toggle','held'):raise ValueError('Invalid repeat mode')
            identifier=entry['id'];name=entry['name']
            if not isinstance(identifier,str) or len(identifier)!=32 or identifier in seen or not all(c in '0123456789abcdef' for c in identifier):raise ValueError('Invalid macro identity')
            if not isinstance(name,str) or not 1<=len(name.strip())<=64:raise ValueError('Invalid macro name')
            validate_macro(entry['tokens'],allow_empty=True)
            seen.add(identifier);result.append(deepcopy(entry))
        return result
    except (ValueError,TypeError):raise ValueError('Macro library is invalid; existing file is preserved') from None


def create(name,tokens=None):
    name=name.strip() if isinstance(name,str) else ''
    if not 1<=len(name)<=64:raise ValueError('Macro name must contain 1..64 characters')
    tokens=deepcopy(tokens or []);validate_macro(tokens,allow_empty=True)
    return {'id':uuid.uuid4().hex,'name':name,'tokens':tokens}
