import json
from glob import glob
import sys
import os
import pickle
import argparse
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction import DictVectorizer
from sklearn.model_selection import train_test_split
# from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report
from sklearn.metrics import precision_score
from sklearn.metrics import accuracy_score

ALL_FEATURES = ["1_top_domains_id_0", "1_top_domains_percent_0", "5_top_domains_id_0", "5_top_domains_id_1", "5_top_domains_id_2", "5_top_domains_id_3", "5_top_domains_id_4", "5_top_domains_percent_0", "5_top_domains_percent_1", "5_top_domains_percent_2", "5_top_domains_percent_3", "5_top_domains_percent_4", "argessive_link_mismatch", "benevolent_link_mismatch", "body_richness", "camouflage", "extractedHrefUrlsDomainCount", "extractedHrefUrlsTotalCount", "extractedSrcUrlsDomainCount", "extractedSrcUrlsTotalCount", "fake_https", "href_camouflaging", "html_form", "in-reply-to", "is_html", "long-email", "many_emails", "max_num_dots_urls", "max_num_slashes_urls", "ner_domain_detected", "num_attachments", "num_black_sheep_link", "num_black_sheep_link_global", "num_black_sheep_link_phish", "num_domain_phish", "num_external_links", "num_freehost_urls", "num_html_script_tags", "num_https_urls", "num_ip_urls", "num_non_80_port_urls", "num_of_chars", "num_param_phish", "num_path_phish", "num_phish_keywords", "num_sender_diff_url", "num_shortened_urls", "num_subdomain_phish", "num_subject_phish_keywords", "num_text_forms", "num_tld_in_url_path", "num_www_in_url_path", "phish_form", "reference_count", "subject_phish_keywords", "subject_richness", "text_and_href", "text_link_with_path", "txt_form", "word_count"]

class ShowHelpOnErrorParser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write('error: %s\n' % message)
        self.print_help()
        sys.exit(2)

SRC_PATH = os.path.dirname(os.path.realpath(__file__))
DATA_PATH = os.path.join(SRC_PATH,"../../data/feature_data")
RES_PATH = os.path.join(SRC_PATH,"../../results")

parser = ShowHelpOnErrorParser()
parser.add_argument("data", type=str,
                    help="data to use, from directory: <{0}>".format(DATA_PATH))
parser.add_argument("-x", "--dontAddUrlFeatures", action="count", default=0,
                    help="data to use, from directory: <{0}>".format(DATA_PATH))
parser.add_argument("-o", "--useOnlyNthFeature", type=int, default=None,
                    help="use only Nth feature")
opt = parser.parse_args()

SUFFIX = "_" + opt.data 
if opt.dontAddUrlFeatures:
    SUFFIX += "X"
if opt.useOnlyNthFeature is not None:
    SUFFIX += str(opt.useOnlyNthFeature)
DATA_VERSION = opt.data
PATH = os.path.join(DATA_PATH, DATA_VERSION)
if not os.path.exists(PATH):
    print("Data not found - directory does not exist <{0}>".format(PATH))
    sys.exit(3)

def load_data():
    data = []
    for cls, pth in [(0, "negative"), (1, "positive")]:
        for i in glob(os.path.join(PATH, pth, "*")):
            try:
                d = json.load(open(i, "r"))
                phish = d.get("phishing", {})
                if "suspicious_links" in phish:
                    phish.pop("suspicious_links")
                if not opt.dontAddUrlFeatures:
                    phish.update({
                        "extractedHrefUrlsDomainCount":
                            d.get("extractedHrefUrlsDomainCount", 0),
                        "extractedHrefUrlsTotalCount":
                            d.get("extractedHrefUrlsTotalCount", 0),
                        "extractedSrcUrlsDomainCount":
                            d.get("extractedSrcUrlsDomainCount", 0),
                        "extractedSrcUrlsTotalCount":
                            d.get("extractedSrcUrlsTotalCount", 0),
                        "word_count": d.get("word_count", 0),
                    })
                if opt.useOnlyNthFeature is not None:
                    if opt.useOnlyNthFeature >= len(ALL_FEATURES):
                        print("'-o' index out of range ({0})".format(len(phish)))
                        sys.exit(4)
                    key = ALL_FEATURES[opt.useOnlyNthFeature]
                    value = 0
                    if key in phish:
                        value = phish[key]
                    tmp = {key:value} 
                    phish = tmp
                data.append((phish, cls))
            except Exception as e:
                print(e, file=sys.stderr)
    return data


def vectorize(x):
    dv = DictVectorizer()
    arr = dv.fit_transform(x)
    feature_names = dv.get_feature_names()
    print("features {}".format(feature_names))
    filename = os.path.join(RES_PATH,"feature_names"+SUFFIX+".json")
    with open(filename, "w") as f:
        f.write(json.dumps(dv.get_feature_names()))
        print("Features stored to {}".format(filename))
    return arr.toarray()


if __name__ == "__main__":
    data = load_data()
    xd = [i[0] for i in data]
    y = [i[1] for i in data]
    print("Data loaded, samples {}".format(len(data)))
    x = vectorize(xd)
    print("x data")
    print(x)
    x_train, x_test, y_train, y_test = train_test_split(x, y, random_state=42)
    clf = RandomForestClassifier(n_estimators=10)
    #RandomForestClassifier(max_depth=5, n_estimators=10, max_features=1)
    print("Starting training")
    model = clf.fit(x_train, y_train)
    print("Model trained")
    model_file = os.path.join(RES_PATH,"model"+SUFFIX+".pkl")
    pickle.dump(model, open(model_file, "wb"))
    print("Model stored to {}".format(model_file))
    print()
    predicted = model.predict(x_test)
    report = ""
    report += 'Precision:\t{}\n'.format(precision_score(y_test, predicted,
                                           average='weighted'))
    report += 'Accuracy:\t{}\n'.format(accuracy_score(y_test, predicted))
    report += '\n'
    report += classification_report(y_test, predicted)
    print(report)
    report_file = os.path.join(RES_PATH,"report"+SUFFIX+".txt")
    with open(report_file, "w") as f:
        f.write(report)
    print("Report stored to {}".format(report_file))

