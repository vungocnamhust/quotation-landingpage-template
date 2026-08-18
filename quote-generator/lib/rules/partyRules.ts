/**
 * Pure domain rules for party composition, guest identity, and greeting labels (TypeScript).
 */

export function resolveClientDisplayName(
  role: string | null | undefined,
  customerName: string | null | undefined,
  clientName?: string | null
): string {
  const isAdvisor = (role || "").trim().toLowerCase() === "advisor";
  const cName = (clientName || "").trim();
  const custName = (customerName || "").trim();

  if (isAdvisor && cName) {
    return cName;
  }
  return custName || "Valued Client";
}

export function generatePartyLabel(
  adults: number | null | undefined,
  children: number | null | undefined = 0,
  customerName?: string | null,
  lang: string = "en"
): string {
  const safeAdults = adults && adults > 0 ? adults : 2;
  const safeKids = children && children > 0 ? children : 0;

  let adultStr = `${safeAdults} Adult${safeAdults > 1 ? "s" : ""}`;
  let kidStr = safeKids > 0 ? `${safeKids} Child${safeKids > 1 ? "ren" : ""}` : "";

  if (lang === "vi") {
    adultStr = `${safeAdults} Người lớn`;
    kidStr = safeKids > 0 ? `${safeKids} Trẻ em` : "";
  } else if (lang === "ar") {
    adultStr = `${safeAdults} بالغ${safeAdults > 1 ? "ين" : ""}`;
    kidStr = safeKids > 0 ? `${safeKids} ${safeKids > 1 ? "أطفال" : "طفل"}` : "";
  }

  const partyCounts = [adultStr, kidStr].filter(Boolean).join(", ");
  const name = (customerName || "").trim();

  if (name && partyCounts) {
    return `${name} & Party (${partyCounts})`;
  }
  if (name) {
    return name;
  }
  return partyCounts;
}

export function inferGreetingName(customerName: string | null | undefined, lang: string = "en"): string | null {
  const name = (customerName || "").trim();
  if (!name) return null;

  const nameLower = name.toLowerCase();
  if (lang === "vi") {
    if (nameLower.startsWith("kính gửi") || nameLower.startsWith("thân gửi")) return name;
    return `Kính gửi ${name}`;
  }
  if (lang === "ar") {
    if (nameLower.startsWith("عزيزي") || nameLower.startsWith("السيد")) return name;
    return `عزيزي ${name}`;
  }

  if (nameLower.startsWith("dear ")) return name;
  return `Dear ${name}`;
}
