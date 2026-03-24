class Old:
    def load_config(config_path: str) -> Dict:
        try:
            with open(config_path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            logging.error(f"Config file not found: {config_path}")
            return {}
        except json.JSONDecodeError:
            logging.error(f"Invalid JSON in config file: {config_path}")
            return {}

    def get_configs(channel_name: str) -> Tuple[Dict, Dict]:
        channel_config_path = os.path.join(Youtube.configs, f"{channel_name}.json")
        global_config_path = os.path.join(Youtube.configs, "global.json")

        channel_config = load_config(channel_config_path)
        global_config = load_config(global_config_path)

        if not channel_config:
            logging.error(f"Configuration for channel '{channel_name}' not found.")
        if not global_config:
            logging.error("Global configuration not found.")

        return channel_config, global_config
