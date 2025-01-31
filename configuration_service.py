import json
import logging


class ConfigurationService:
    _instance = None  # Singleton instance

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigurationService, cls).__new__(cls)
            cls._instance._settings = {}  # Storage for settings
        return cls._instance

    def set_config(self, key, value):
        """Sets a configuration value."""
        self._settings[key] = value

    def get_config(self, key, default=None):
        """Retrieves a configuration value."""
        return self._settings.get(key, default)

    def get_all_configs(self):
        """Returns all configuration settings."""
        return self._settings

    def load_from_parser(self, args):
        """Loads configurations from parsed arguments."""
        # Check interval is valid
        if args.interval < 5:
            logging.error("Interval must be at least 5 seconds.")
            exit(1)

        self.set_config("storage_dir", args.storage_dir)
        self.set_config("discord_webhook_url", args.webhook)
        self.set_config("mention_users", args.mention_users.split(",") if args.mention_users else None)
        self.set_config("interval", args.interval)

        # Parse rules JSON
        try:
            rules = json.loads(args.rules)
            self.validate_rules(rules)
            self.set_config("rules", rules)
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse rules JSON: {e}")
            exit(1)

        # Optional user agents
        self.set_config("webpage_user_agent", args.webpage_user_agent)
        self.set_config("webpage_selenium_user_agent", args.webpage_selenium_user_agent)
        self.set_config("api_user_agent", args.api_user_agent)
    
    def validate_rules(self, rules):
        """Validates that each rule has either 'api_check' or 'webpage_check' with required fields."""
        if not isinstance(rules, dict):
            raise ValueError("Rules should be a dictionary.")

        for url, rule in rules.items():
            if "api_check" not in rule and "webpage_check" not in rule:
                raise ValueError(f"Rule for {url} must specify either 'api_check' or 'webpage_check'.")

            if rule.get("api_check"):
                if "json_selectors" not in rule or not isinstance(rule["json_selectors"], list) or not rule["json_selectors"]:
                    raise ValueError(f"API rule for {url} requires a non-empty 'json_selectors' list.")

            if rule.get("webpage_check"):
                if "selectors" not in rule or not isinstance(rule["selectors"], list) or not rule["selectors"]:
                    raise ValueError(f"Webpage rule for {url} requires a non-empty 'selectors' list.")
