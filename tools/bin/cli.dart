import 'package:args/args.dart';
import 'package:dart_cli/build.dart';

void main(List<String> arguments) {
  final ArgParser argParser = new ArgParser()
    ..addOption('build-settings',
        abbr: 's',
        defaultsTo: 'build_settings.yaml',
        help: "webrtc build seetings file?")
    ..addFlag('help',
        abbr: 'h', negatable: false, help: "Displays this help information.");

  ArgResults argResults = argParser.parse(arguments);
  if (argResults['help']) {
    print("""
** WebRTC Build CLI **
${argParser.usage}
    """);
  }
  final String settingFile = argResults['build-settings'];
  build(Options()..settings = settingFile);
}
