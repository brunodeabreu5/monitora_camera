# User Repository (FASE 3.1 - Repository Pattern)
"""
Repository para gerenciamento de usuários.

Encapsula operações de CRUD de usuários, abstraindo o acesso
ao arquivo de configuração JSON.
"""

from typing import List, Dict, Any, Optional

from src.core.config import AppConfig


class UserRepository:
    """
    Repository para acesso e manipulação de usuários.

    Fornece interface limpa para gerenciar usuários sem expor
    a complexidade do formato de configuração e hash de senhas.

    Attributes:
        config: Instância de AppConfig para acesso às configurações

    Example:
        >>> repo = UserRepository(config)
        >>> user = repo.find_by_username("admin")
        >>> repo.create({"username": "joao", "password": "senha123"})
    """

    def __init__(self, config: AppConfig):
        """
        Inicializa repository com configuração da aplicação.

        Args:
            config: Instância de AppConfig
        """
        self.config = config

    def find_all(self) -> List[Dict[str, Any]]:
        """
        Retorna todos os usuários.

        Returns:
            List[Dict]: Lista de usuários (sem senha em texto claro)
        """
        return self.config.data.get("users", [])

    def find_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Busca usuário por nome de usuário.

        Args:
            username: Nome de usuário único

        Returns:
            Optional[Dict]: Dicionário com dados do usuário ou None
        """
        return self.config.get_user(username)

    def authenticate(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Autentica usuário com nome e senha.

        Args:
            username: Nome de usuário
            password: Senha em texto claro

        Returns:
            Optional[Dict]: Dados do usuário se autenticado com sucesso, None se falhou
        """
        return self.config.authenticate(username, password)

    def create(self, user_data: Dict[str, Any]) -> None:
        """
        Cria novo usuário.

        Args:
            user_data: Dicionário com dados do usuário. Deve conter:
                - username: Nome de usuário único
                - password: Senha em texto claro (será hasheada)
                - role: Cargo (padrão: "Operador")

        Raises:
            ValueError: Se usuário já existe ou campos obrigatórios faltando
        """
        username = user_data.get("username")
        if not username:
            raise ValueError("username é obrigatório")

        if self.exists(username):
            raise ValueError(f"Usuário '{username}' já existe")

        password = user_data.get("password")
        if not password:
            raise ValueError("password é obrigatório")

        # Hash da senha será feito por upsert_user
        self.config.upsert_user(user_data)
        self.config.save()

    def update(self, user_data: Dict[str, Any]) -> None:
        """
        Atualiza usuário existente.

        Args:
            user_data: Dicionário com dados atualizados do usuário

        Raises:
            ValueError: Se usuário não existe
        """
        username = user_data.get("username")
        if not self.exists(username):
            raise ValueError(f"Usuário '{username}' não encontrado")

        self.config.upsert_user(user_data)
        self.config.save()

    def delete(self, username: str) -> bool:
        """
        Deleta um usuário por nome.

        Args:
            username: Nome do usuário a deletar

        Returns:
            bool: True se deletou com sucesso, False se não encontrou
        """
        if not self.exists(username):
            return False

        self.config.delete_user(username)
        self.config.save()
        return True

    def exists(self, username: str) -> bool:
        """
        Verifica se usuário existe.

        Args:
            username: Nome de usuário

        Returns:
            bool: True se usuário existe, False caso contrário
        """
        return self.find_by_username(username) is not None

    def count(self) -> int:
        """
        Retorna número total de usuários.

        Returns:
            int: Total de usuários cadastrados
        """
        return len(self.find_all())

    def is_empty(self) -> bool:
        """
        Verifica se não há usuários cadastrados.

        Útil para detectar primeira execução.

        Returns:
            bool: True se não há usuários, False caso contrário
        """
        return self.count() == 0

    def requires_password_change(self, username: str) -> bool:
        """
        Verifica se usuário precisa trocar senha.

        Args:
            username: Nome de usuário

        Returns:
            bool: True se precisa trocar senha, False caso contrário
        """
        return self.config.user_requires_password_change(username)

    def change_password(
        self,
        username: str,
        new_password: str,
        old_password: Optional[str] = None
    ) -> bool:
        """
        Altera senha de um usuário.

        Args:
            username: Nome de usuário
            new_password: Nova senha em texto claro
            old_password: Senha atual para verificação (opcional)

        Returns:
            bool: True se alterou com sucesso, False se senha atual não confere

        Raises:
            ValueError: Se usuário não existe
        """
        from src.core.config import hash_password

        user = self.find_by_username(username)
        if not user:
            raise ValueError(f"Usuário '{username}' não encontrado")

        # Verificar senha atual se fornecida
        if old_password is not None:
            from src.core.config import verify_password
            if not verify_password(user, old_password):
                return False

        # Atualizar senha
        pwd_hash, pwd_salt = hash_password(new_password)
        user_data = dict(user)
        user_data["password_hash"] = pwd_hash
        user_data["password_salt"] = pwd_salt
        user_data["must_change_password"] = False

        self.update(user_data)
        return True

    def get_admins(self) -> List[Dict[str, Any]]:
        """
        Retorna todos os usuários com cargo de Administrador.

        Returns:
            List[Dict]: Lista de administradores
        """
        users = self.find_all()
        return [u for u in users if u.get("role") == "Administrador"]

    def has_admins(self) -> bool:
        """
        Verifica se há pelo menos um administrador cadastrado.

        Returns:
            bool: True se há admin, False caso contrário
        """
        return len(self.get_admins()) > 0
