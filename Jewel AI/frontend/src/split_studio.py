import os
import re

with open('D:/Workspace/Jewel AI/Jewel AI/frontend/src/pages/StudioPage.tsx', 'r', encoding='utf-8') as f:
    code = f.read()

start_func = code.find('export function StudioPage() {')
start_logic = start_func + len('export function StudioPage() {')
end_logic = code.find('return (\n    <AppLayout', start_logic)
if end_logic == -1: end_logic = code.find('return (\r\n    <AppLayout', start_logic)

imports = code[:start_func]
logic = code[start_logic:end_logic]
jsx = code[end_logic:]
if jsx.strip().endswith('}'):
    jsx = jsx.strip()[:-1]

top_vars = []
for line in logic.split('\n'):
    if line.startswith('  const ') or line.startswith('  let '):
        decl = line.split('=', 1)[0].replace('const ', '').replace('let ', '').strip()
        if decl.startswith('['):
            inner = decl[1:-1]
            for v in inner.split(','):
                v = v.split(':')[0].split('=')[0].strip()
                if v: top_vars.append(v)
        elif decl.startswith('{'):
            inner = decl[1:-1]
            for v in inner.split(','):
                v = v.split(':')[0].split('=')[0].strip()
                if v: top_vars.append(v)
        else:
            decl = decl.split(':')[0].strip()
            top_vars.append(decl)

top_vars = [v for v in top_vars if re.match(r'^[a-zA-Z_$][a-zA-Z0-9_$]*$', v)]
top_vars = sorted(list(set(top_vars)))

# Missing things from queries not captured by the simple '  const ' detector
if 'options' not in top_vars: top_vars.append('options')
if 'optionsError' not in top_vars: top_vars.append('optionsError')
if 'optionsFetching' not in top_vars: top_vars.append('optionsFetching')
if 'variants' not in top_vars: top_vars.append('variants')
if 'stylePresets' not in top_vars: top_vars.append('stylePresets')
if 'recentJobs' not in top_vars: top_vars.append('recentJobs')
if 'favoriteIdList' not in top_vars: top_vars.append('favoriteIdList')

state_keys = []
dispatch_keys = []

for v in top_vars:
    # heuristic for dispatch vs state
    if v.startswith('set') or v.startswith('clear') or v.startswith('toggle') or v.startswith('on') or v.startswith('upload') or v.endswith('Mutation'):
        dispatch_keys.append(v)
    else:
        state_keys.append(v)

state_keys = sorted(list(set(state_keys)))
dispatch_keys = sorted(list(set(dispatch_keys)))

context_code = imports + """
import { createContext, useContext, ReactNode, useMemo } from 'react';

export const StudioStateContext = createContext<any>(null);
export const StudioDispatchContext = createContext<any>(null);

export function useStudioState() {
  const context = useContext(StudioStateContext);
  if (!context) throw new Error("useStudioState must be used within a StudioProvider");
  return context;
}

export function useStudioDispatch() {
  const context = useContext(StudioDispatchContext);
  if (!context) throw new Error("useStudioDispatch must be used within a StudioProvider");
  return context;
}

export function StudioProvider({ children }: { children: ReactNode }) {
""" + logic + """
  const state = useMemo(() => ({
    """ + ',\n    '.join(state_keys) + """
  }), [""" + ', '.join(state_keys) + """]);

  const dispatch = useMemo(() => ({
    """ + ',\n    '.join(dispatch_keys) + """
  }), [""" + ', '.join(dispatch_keys) + """]);

  return (
    <StudioDispatchContext.Provider value={dispatch}>
      <StudioStateContext.Provider value={state}>
        {children}
      </StudioStateContext.Provider>
    </StudioDispatchContext.Provider>
  );
}
"""

os.makedirs('D:/Workspace/Jewel AI/Jewel AI/frontend/src/pages/studio', exist_ok=True)
with open('D:/Workspace/Jewel AI/Jewel AI/frontend/src/pages/studio/StudioContext.tsx', 'w', encoding='utf-8') as f:
    f.write(context_code)

layout_code = imports + """
import { useStudioState, useStudioDispatch } from "./StudioContext";

export function StudioLayout() {
  const state = useStudioState();
  const dispatch = useStudioDispatch();
  const {
    """ + ',\n    '.join(state_keys) + """
  } = state;
  const {
    """ + ',\n    '.join(dispatch_keys) + """
  } = dispatch;

""" + jsx + """
}
"""
with open('D:/Workspace/Jewel AI/Jewel AI/frontend/src/pages/studio/StudioLayout.tsx', 'w', encoding='utf-8') as f:
    f.write(layout_code)

print("Generated Context and Layout successfully")
