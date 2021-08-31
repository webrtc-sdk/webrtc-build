import 'dart:convert';
import 'dart:io';
import 'package:process_run/process_run.dart';

import 'settings.dart';

class Options {
  String? settings;
}

Future<void> build(Options opts) async {
  print("settingFile, ${opts.settings}!");
  //Map<String, String> env = Platform.environment;
  //env.forEach((k, v) => print("$k => $v\n"));

  Map? config = loadYamlFileSync("build_settings.yaml");
  print(JsonEncoder.withIndent(' ').convert(config));

  Map? downloads = config!['downloads'] as Map;
  downloads.forEach((k, v) async {
    await download(v['repo'], v['branch'], v['path']);
  });
}

Future<void> download(String? repo, String? branch, String? out_path) async {
  bool exists = await Directory(out_path!).exists();
  if (!exists) {
    print("downloading! repo = $repo, branch = $branch, path=$out_path");
    var result = await runExecutableArguments(
        'git',
        [
          'clone',
          if (branch != null) '-b',
          if (branch != null) '$branch',
          '$repo',
          '$out_path'
        ],
        verbose: true);
    if (result.exitCode != 0) {
      print("git clone failed!");
    }
  } else {
    print('file [$out_path] exists, skip to download.');
  }
}
