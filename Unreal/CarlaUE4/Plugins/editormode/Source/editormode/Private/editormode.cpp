// Copyright Epic Games, Inc. All Rights Reserved.

#include "editormode.h"
#include "editormodeEdMode.h"

#define LOCTEXT_NAMESPACE "FeditormodeModule"

void FeditormodeModule::StartupModule()
{
	// This code will execute after your module is loaded into memory; the exact timing is specified in the .uplugin file per-module
	FEditorModeRegistry::Get().RegisterMode<FeditormodeEdMode>(FeditormodeEdMode::EM_editormodeEdModeId, LOCTEXT("editormodeEdModeName", "editormodeEdMode"), FSlateIcon(), true);
}

void FeditormodeModule::ShutdownModule()
{
	// This function may be called during shutdown to clean up your module.  For modules that support dynamic reloading,
	// we call this function before unloading the module.
	FEditorModeRegistry::Get().UnregisterMode(FeditormodeEdMode::EM_editormodeEdModeId);
}

#undef LOCTEXT_NAMESPACE
	
IMPLEMENT_MODULE(FeditormodeModule, editormode)