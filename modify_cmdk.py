import sys

with open('apps/web/components/CmdkSearch.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# Add useTheme import
import_line = 'import { useRouter } from "next/navigation";\n'
new_import = import_line + 'import { useTheme } from "./ThemeProvider";\n'
content = content.replace(import_line, new_import)

# Add useTheme hook
hook_line = '  const router = useRouter();\n'
new_hook = hook_line + '  const { theme, setTheme } = useTheme();\n'
content = content.replace(hook_line, new_hook)

# Add command group for actions inside Command.List
old_list = '''          <Command.List className="max-h-[60vh] overflow-y-auto p-2">
            <Command.Empty className="p-6 text-center text-sm text-[var(--color-text-secondary)]">
              {loading ? "Searching..." : "No contracts found."}
            </Command.Empty>'''

new_list = '''          <Command.List className="max-h-[60vh] overflow-y-auto p-2">
            <Command.Empty className="p-6 text-center text-sm text-[var(--color-text-secondary)]">
              {loading ? "Searching..." : "No results found."}
            </Command.Empty>

            <Command.Group heading="Commands" className="text-xs font-semibold text-[var(--color-text-secondary)] mb-2 px-2 mt-4 first:mt-0">
              <Command.Item
                onSelect={() => {
                  router.push(/contracts/new);
                  setOpen(false);
                }}
                className="flex items-center gap-3 px-3 py-3 text-sm text-[var(--color-text-primary)] rounded-md cursor-pointer data-[selected=true]:bg-[var(--color-bg-hover)] data-[selected=true]:text-[var(--color-text-primary)]"
              >
                Track contract
              </Command.Item>
              <Command.Item
                onSelect={() => {
                  setTheme(theme === "dark" ? "light" : "dark");
                  setOpen(false);
                }}
                className="flex items-center gap-3 px-3 py-3 text-sm text-[var(--color-text-primary)] rounded-md cursor-pointer data-[selected=true]:bg-[var(--color-bg-hover)] data-[selected=true]:text-[var(--color-text-primary)]"
              >
                Toggle theme
              </Command.Item>
            </Command.Group>
            
            {results.length > 0 && (
              <Command.Group heading="Contracts" className="text-xs font-semibold text-[var(--color-text-secondary)] px-2 mt-4">
'''

content = content.replace(old_list, new_list)

# Close the new group
old_results = '''              </Command.Item>
            ))}
          </Command.List>'''

new_results = '''              </Command.Item>
            ))}
            </Command.Group>
            )}
          </Command.List>'''
content = content.replace(old_results, new_results)

with open('apps/web/components/CmdkSearch.tsx', 'w', encoding='utf-8') as f:
    f.write(content)
