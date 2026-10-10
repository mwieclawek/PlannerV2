# -*- coding: utf-8 -*-
import re

with open('frontend/lib/screens/sysadmin/sysadmin_dashboard.dart', 'r', encoding='utf-8') as f:
    content = f.read()

card_replacement = '''
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Expanded(
                              child: Text(
                                '\ (ID: \)',
                                style: const TextStyle(
                                  fontSize: 18,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ),
                            IconButton(
                              icon: const Icon(Icons.edit),
                              onPressed: () => _showEditRestaurantDialog(r['id'], r['name'], r['slug']),
                              tooltip: 'Edytuj restaurację',
                            ),
                            Switch(
                              value: isActive,
                              onChanged: (val) => _toggleStatus(r['id'], isActive),
                              activeColor: Colors.purple,
                            ),
                          ],
                        ),
                        Text(
                          'Login ID: \',
                          style: TextStyle(color: Colors.grey.shade700),
                        ),
                        const SizedBox(height: 8),
                        Row(
                          children: [
                            Icon(Icons.people, size: 16, color: Colors.grey.shade600),
                            const SizedBox(width: 4),
                            Text('\ użytkowników'),
                            const SizedBox(width: 16),
                            Icon(Icons.admin_panel_settings,
                                size: 16, color: Colors.grey.shade600),
                            const SizedBox(width: 4),
                            Text('\ managerów'),
                          ],
                        ),
                        const SizedBox(height: 16),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.end,
                          children: [
                            OutlinedButton.icon(
                              icon: const Icon(Icons.people),
                              label: const Text('Użytkownicy'),
                              onPressed: () => _showUsersDialog(r['id'], r['name']),
                            ),
                            const SizedBox(width: 8),
                            OutlinedButton.icon(
                              icon: const Icon(Icons.person_add),
                              label: const Text('Dodaj managera'),
                              onPressed: () => _showAddManagerDialog(r['id'], r['name']),
                            ),
                          ],
                        ),
'''

content = re.sub(r'Row\(\s*mainAxisAlignment: MainAxisAlignment.spaceBetween,\s*children: \[\s*Expanded\(.*?\),\s*\],.*?\),', card_replacement, content, flags=re.DOTALL)

with open('frontend/lib/screens/sysadmin/sysadmin_dashboard.dart', 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated sysadmin_dashboard.dart")
