Pod::Spec.new do |spec|
  spec.name = "LiveKitWebRTC"
  spec.version = "{{VERSION}}"
  spec.summary = "Custom WebRTC build for LiveKit"
  spec.description = <<-DESC
    LiveKit version Dynamic WebRTC XCFramework
    * Framework is renamed to LiveKitWebRTC.
    * Objective-C symbols are prefixed with LK, for example LKRTCPeerConnection.
  DESC

  spec.homepage = "https://github.com/livekit/webrtc-xcframework"
  spec.license = {:type => "BSD", :file => "LiveKitWebRTC.xcframework/LICENSE"}
  spec.author = "LiveKit"

  spec.ios.deployment_target = "13.0"
  spec.osx.deployment_target = "10.15"
  spec.tvos.deployment_target = "17.0"
  spec.visionos.deployment_target = "26.0"

  spec.source = {
    :http => "https://github.com/livekit/webrtc-xcframework/releases/download/{{VERSION}}/LiveKitWebRTC.xcframework.zip"
  }
  spec.vendored_frameworks = "LiveKitWebRTC.xcframework"

  # Exclude architectures for specific platforms
  spec.pod_target_xcconfig = {
    'EXCLUDED_ARCHS[sdk=appletvsimulator*]' => 'x86_64',
    'EXCLUDED_ARCHS[sdk=xrsimulator*]' => 'x86_64'
  }
end
