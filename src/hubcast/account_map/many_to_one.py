from typing import Union

from .abc import AccountMap


class ManyToOneMap(AccountMap):
    """
    A simple user map importing from a YAML file of the form.

    Users:
      github_user: gitlab_user
      github_user2: gitlab_user2

    Attributes
    ----------
    path: str
        A filepath to the users.yml defining a usermapping.
    """

    def __init__(self, user: str):
        self.user = user

    def __call__(self, github_user: str) -> Union[str, None]:
        return self.user
