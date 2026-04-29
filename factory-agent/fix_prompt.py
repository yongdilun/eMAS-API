import sys
path = 'agent/reasoning_pipeline.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old_rule = '"- Do not invent unsupported args.\\n\\n"'
new_rule = '"- Do not invent unsupported args.\\n"\n                "- Populate optional_args into args if they match the intent.\\n\\n"'

if old_rule in content:
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content.replace(old_rule, new_rule))
    print('Replaced rule successfully')
else:
    print('Rule not found')
