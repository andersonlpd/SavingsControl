import sys
from getpass import getpass

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import RecoveryDevice


class Command(BaseCommand):
    help = "Cria a única conta permitida e exibe os códigos de recuperação uma vez."

    def add_arguments(self, parser):
        parser.add_argument("username")

    def handle(self, *args, **options):
        User = get_user_model()
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            raise CommandError(
                "O provisionamento exige um terminal interativo para proteger a senha e os códigos."
            )
        if User.objects.exists():
            raise CommandError("Já existe uma conta. A aplicação aceita apenas um usuário.")

        password = getpass("Senha (mínimo de 12 caracteres): ")
        confirmation = getpass("Confirme a senha: ")
        if password != confirmation:
            raise CommandError("As senhas não coincidem.")
        validate_password(password)

        with transaction.atomic():
            user = User.objects.create_user(username=options["username"], password=password)
            recovery_codes = RecoveryDevice.issue_codes(user)
        self.stdout.write(
            self.style.SUCCESS("Conta criada. Configure o TOTP em /account/two_factor/setup/.")
        )
        self.stdout.write("Guarde estes códigos agora; cada código só pode ser usado uma vez:")
        self.stdout.write("\n".join(recovery_codes))
