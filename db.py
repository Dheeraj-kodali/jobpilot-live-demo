"""User-scoped PostgREST access. Never accepts a caller-supplied owner."""
from fastapi import HTTPException
from accounts import identity, remote

TABLES = {'profiles', 'resumes', 'claims', 'evidence_links', 'job_sources',
          'user_jobs', 'applications', 'application_events'}


class UserDB:
    def __init__(self, request):
        self.token, self.user_id = identity(request)

    def query(self, table, method='GET', values=None, record_id=None):
        if table not in TABLES:
            raise ValueError('Unknown table')
        params = {'user_id': 'eq.' + self.user_id}
        if record_id:
            from uuid import UUID
            params['id'] = 'eq.' + str(UUID(str(record_id)))
        kwargs = {'params': params}
        if method == 'GET':
            params.update(select='*', limit='100')
        if values is not None:
            if 'user_id' in values and values['user_id'] != self.user_id:
                raise HTTPException(403, 'Record belongs to another account.')
            kwargs['json'] = dict(values, user_id=self.user_id)
            kwargs['headers'] = {'Prefer': 'return=representation' +
                                 (',resolution=merge-duplicates' if table == 'profiles' else '')}
        return remote(method, '/rest/v1/' + table, self.token, **kwargs)
