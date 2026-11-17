import { File } from "expo-file-system";
import { Platform } from "react-native";

export type MultipartAsset = {
  uri: string;
  fileName?: string | null;
  mimeType?: string | null;
};

/**
 * Expo SDK 58's fetch implementation expects a real Blob/File. The legacy
 * React Native `{ uri, name, type }` object fails before the request is sent.
 */
export async function appendAssetToFormData(
  form: FormData,
  field: string,
  asset: MultipartAsset,
  fallbackName: string,
) {
  const fileName = asset.fileName || fallbackName;

  if (Platform.OS === "web") {
    const response = await fetch(asset.uri);
    if (!response.ok) throw new Error("The selected image could not be read.");
    form.append(field, await response.blob(), fileName);
    return;
  }

  form.append(field, new File(asset.uri), fileName);
}
