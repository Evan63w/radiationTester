import unittest

from streamlit.testing.v1 import AppTest


class DashboardTests(unittest.TestCase):
    def test_saving_and_extreme_composition(self):
        app = AppTest.from_file("app.py", default_timeout=30).run()
        self.assertFalse(app.exception)
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.dataframe), 1)
        app.slider[0].set_value(100).run()
        self.assertFalse(app.exception)
        app.number_input[1].set_value(20000.0).run()
        self.assertFalse(app.exception)


if __name__ == "__main__":
    unittest.main()
