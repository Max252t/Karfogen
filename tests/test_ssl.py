import unittest

import support
from AIAssistant.agent import llm_client


class SslContextTest(unittest.TestCase):
    def test_bundled_root_is_trusted(self):
        names = []
        for cert in llm_client._ssl_context().get_ca_certs():
            for part in cert.get("subject", ()):
                for key, value in part:
                    if key == "commonName":
                        names.append(value)
        self.assertIn("GlobalSign Root R46", names)

    def test_verification_can_be_disabled(self):
        from AIAssistant import config
        config.set_value("verify_ssl", False)
        try:
            context = llm_client._ssl_context()
            self.assertFalse(context.check_hostname)
        finally:
            config.set_value("verify_ssl", True)


if __name__ == "__main__":
    unittest.main()
