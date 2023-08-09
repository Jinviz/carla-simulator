// Copyright Epic Games, Inc. All Rights Reserved.

#include "editormodeEdMode.h"
#include "editormodeEdModeToolkit.h"
#include "Toolkits/ToolkitManager.h"
#include "EditorModeManager.h"

const FEditorModeID FeditormodeEdMode::EM_editormodeEdModeId = TEXT("EM_editormodeEdMode");

FeditormodeEdMode::FeditormodeEdMode()
{

}

FeditormodeEdMode::~FeditormodeEdMode()
{

}

void FeditormodeEdMode::Enter()
{
	FEdMode::Enter();

	if (!Toolkit.IsValid() && UsesToolkits())
	{
		Toolkit = MakeShareable(new FeditormodeEdModeToolkit);
		Toolkit->Init(Owner->GetToolkitHost());
	}
}

void FeditormodeEdMode::Exit()
{
	if (Toolkit.IsValid())
	{
		FToolkitManager::Get().CloseToolkit(Toolkit.ToSharedRef());
		Toolkit.Reset();
	}

	// Call base Exit method to ensure proper cleanup
	FEdMode::Exit();
}

bool FeditormodeEdMode::UsesToolkits() const
{
	return true;
}




