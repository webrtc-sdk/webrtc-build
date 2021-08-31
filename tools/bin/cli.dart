import 'package:args/args.dart';
import '../lib/build.dart';

void main(List<String> arguments) {
  final ArgParser argParser = new ArgParser()
    ..addOption('build-settings',
        abbr: 's',
        defaultsTo: 'webrtc_build_settings.yaml',
        help: "webrtc build seetings file?")
    ..addFlag('help',
        abbr: 'h', negatable: false, help: "Displays this help information.");

  ArgResults argResults = argParser.parse(arguments);
  if (argResults['help']) {
    print("""
** WebRTC Build CLI **
${argParser.usage}
    """);
    return;
  }
  final String settingFile = argResults['build-settings'];
  build(Options()..settings = settingFile);
}
