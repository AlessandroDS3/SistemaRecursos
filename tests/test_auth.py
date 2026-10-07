import unittest
from unittest.mock import MagicMock, patch
from app.auth import password_hash, verify_password, AuthService

class AuthTest(unittest.TestCase):
    def test_password_hash_and_salt(self):
        first=password_hash('Contraseña segura 123')
        self.assertTrue(verify_password('Contraseña segura 123',first))
        self.assertFalse(verify_password('otra',first))
        self.assertNotEqual(first,password_hash('Contraseña segura 123'))
        self.assertNotIn('Contraseña',first)

    def test_expiry_and_inactive(self):
        repo=MagicMock();repo.obtener.return_value={'nombreUsuario':'prueba','contrasenaHash':password_hash('Clave-123456'),'activo':True}
        service=AuthService(repo)
        with patch('app.auth.time.monotonic',return_value=10):
            token=service.login('prueba','Clave-123456','local')
            self.assertEqual(service.session(token),'prueba')
        with patch('app.auth.time.monotonic',return_value=28811):
            self.assertIsNone(service.session(token))
        repo.obtener.return_value['activo']=False
        self.assertIsNone(service.login('prueba','Clave-123456','local'))
