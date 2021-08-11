class Utils:
    """All the utility methods"""
    print_ = print

    @staticmethod
    def parse_config_file(verbose=False):
        """parsing config.json"""
        import os

        def print(*args, **kwargs):
            if verbose:
                Utils.print_(*args, **kwargs)

        if os.path.exists('./config.json'):
            print('ok')
        else:
            with open('config.json', 'w') as f:
                f.write('{"version":"1.0.0","vide_directory_absolute":[],"max_HLS_folder_size_GB":1}')
            raise FileNotFoundError('Unable to find config.json in the directory. Creating a new config.json,'
                                    ' please add the video folder absolute paths inside "vide_directory_absolute": []')


if __name__ == '__main__':
    Utils.parse_config_file()
    Utils.parse_config_file(True)
