import sdk.connection
import db
import models.workspace
import models.document
import config
import sdk.utils
import sys
import sdk.html


class Structure(object):
    def __init__(self):
        db.DBConnection().verify_db()

    @classmethod
    def workspaces_from_db(cls, dbconn):
        workspace_map = {}
        rows = dbconn.fetchall('SELECT id, name FROM workspaces')
        for row in rows:
            workspace_map[row[0]] = {
                'id': row[0],
                'name': row[1]
            }

        return workspace_map

    def synchronize(self):
        workspaces = sdk.connection.account_workspaces()
        if config.conf.WORKSPACE_IDS:
            print('Limited sync, check config for specific workspaces synchronized')
            workspaces = [w for w in workspaces if w.id in config.conf.WORKSPACE_IDS]
        workspaces_ids = [w.id for w in workspaces]

        with db.DBConnection() as dbconn:
            existing_workspace_map = self.workspaces_from_db(dbconn)
            for workspace in workspaces:
                if workspace.id not in existing_workspace_map:
                    print('Adding', workspace, 'to DB')
                    dbconn.update('INSERT INTO workspaces (id, name) VALUES (?, ?)', (workspace.id, workspace.name))
                elif workspace.name != existing_workspace_map[workspace.id]['name']:
                    print('Updating name of', workspace)
                    dbconn.update('UPDATE workspaces SET name = ? WHERE id = ?', (workspace.name, workspace.id))

        for _id, ws in existing_workspace_map.items():
            if _id not in workspaces_ids:
                print('Workspace', _id, ws['name'], 'seems to be archived - not touching')

        print('Workspaces updated, moving on to documents')

        for workspace in workspaces:
            containers, documents, urls = sdk.connection.workspace_documents(workspace.id)

            for c in containers:
                c.update_or_insert()

            for d in documents:
                d.update_or_insert()

            for u in urls:
                u.update_or_insert()

        users = sdk.connection.account_members()

        for u in users:
            u.update_or_insert()

    @classmethod
    def download_docs(cls):
        documents = models.document.Document.by_pending_download()
        no = len(documents)
        current = 1
        previous_len = 0
        for document in documents:
            sys.stdout.write('\r' + ' ' * previous_len)
            sys.stdout.flush()
            document_name = document.name if len(document.name) < 60 else document.name[0:50] + '...' + document.name[-5:]
            to_print = 'Downloading: %d / %d (%s)' % (current, no, document_name)
            previous_len = len(to_print)
            sys.stdout.write('\r' + to_print)
            sys.stdout.flush()
            document.download()
            current += 1
        sys.stdout.write('\n')

    @classmethod
    def render_html(self):
        with db.DBConnection() as dbconn:
            workspace_rows = dbconn.fetchall('SELECT name, id FROM workspaces ORDER BY name ASC')
            workspaces = [
                models.workspace.Workspace(*row) for row in workspace_rows
            ]

        for workspace in workspaces:
            workspace.render_html()

        sdk.html.render_index_page(workspaces)
