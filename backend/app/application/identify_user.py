from uuid import UUID

from app.application.ports import TokenVerifier, UserRepository


class IdentifyUser:
    def __init__(self, verifier: TokenVerifier, users: UserRepository) -> None:
        self._verifier = verifier
        self._users = users

    def run(self, token: str) -> UUID:
        return self._users.id_of(self._verifier.subject_of(token))
