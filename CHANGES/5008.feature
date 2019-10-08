Add new `repo_key` class attribute to `Content` which defaults to an empty tuple. Subclasses should
use `repo_key` to specify the names of fields, which together should be unique per Repository.
Anytime `RepositoryVersion.add_content()` is called, it now automatically removes content that
matches the `repo_key`.
