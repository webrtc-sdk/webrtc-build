import 'dart:io';

import 'package:yaml/yaml.dart';

Map? loadYamlFileSync(String path) {
  File file = new File(path);
  if (file.existsSync() == true) {
    return loadYaml(file.readAsStringSync());
  }
  return null;
}

Future<Map?> loadYamlFile(String path) async {
  File file = new File(path);
  if ((await file.exists()) == true) {
    String content = await file.readAsString();
    return loadYaml(content);
  }
  return null;
}
