import subprocess
import ast
from eos.utils.product_features import unsupported_features

storage_type = "physical"
server_type = "Virtual"

try:
    setup_info = subprocess.Popen(['sudo', 'provisioner', 'get_setup_info'],
        stdout=subprocess.PIPE).communicate()[0].decode("utf-8").rstrip()
    setup_info = ast.literal_eval(setup_info)
    storage_type = setup_info['storage_type'].lower()
    server_type = setup_info['server_type'].lower()
    print(f"Storage Type : '{storage_type}'")
    print(f"Server Type '{server_type}'")
    if (storage_type=="virtual") and (server_type=="virtual"):
        print("Unsupported features adding into unsupported feature Database.")
        unsupported_feature_instance = unsupported_features.UnsupportedFeaturesDB()
        unsupported_feature_instance.store_unsupported_features(component_name="sspl", features=["health"])
        print("Unsupported feature list added sucessfully.")
except Exception as err:
    print(f"Error in getting setup information : {err}")
    print(f"Considering default storage type : '{storage_type}'")
    print(f"Considering default server type : '{server_type}'")
